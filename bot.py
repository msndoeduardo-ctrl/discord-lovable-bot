import discord
from discord.ext import commands
import os
import asyncio
import threading
import requests
from fastapi import FastAPI, Request
import uvicorn

# ======================
# CONFIGURAÇÕES
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID_ENV = os.getenv("DISCORD_GUILD_ID")
if not GUILD_ID_ENV:
    raise Exception("DISCORD_GUILD_ID não configurado")
GUILD_ID = int(GUILD_ID_ENV)

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = "https://discord-lovable-bot.onrender.com/auth/discord/callback"

CATEGORY_ID = 1468013305204445250
CHANNEL_BUTTON_ID = 1468013455712714873
SUPPORT_ROLE_ID = 1468012075551948944

ROLE_MAP = {
    "bronze": 1468740290658566276,
    "prata": 1467901642195337380,
    "prata2": 1467901956021555311,
    "ouro": 1467902182979407912,
    "elite": 1467902327036969159,
    "expansao": 1467902455659364414
}

TICKET_COUNTER_FILE = "ticket_counter.txt"

# ======================
# FASTAPI
# ======================
app = FastAPI()

async def apply_role(discord_id: int, role_id: int, action: str):
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    member = guild.get_member(discord_id)
    role = guild.get_role(role_id)

    if not member or not role:
        return

    if action == "add":
        await member.add_roles(role)
    elif action == "remove":
        await member.remove_roles(role)

@app.post("/discord/webhook")
async def discord_webhook(req: Request):
    data = await req.json()

    discord_id = int(data.get("discord_id"))
    plano = data.get("plano")
    action = data.get("acao", "add")

    role_id = ROLE_MAP.get(plano)
    if not role_id:
        return {"error": "Plano inválido"}

    bot.loop.create_task(apply_role(discord_id, role_id, action))
    return {"status": "ok"}

# ======================
# OAUTH DISCORD (NOVA ROTA)
# ======================
@app.get("/auth/discord/callback")
async def discord_callback(code: str, state: str = None):
    token_url = "https://discord.com/api/oauth2/token"

    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify email",
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_res = requests.post(token_url, data=data, headers=headers)
    token_res.raise_for_status()
    token_json = token_res.json()

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token_json['access_token']}"}
    )
    user_res.raise_for_status()

    return {
        "discord_user": user_res.json()
    }

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

# ======================
# CONTADOR
# ======================
def get_next_ticket_number():
    if not os.path.exists(TICKET_COUNTER_FILE):
        with open(TICKET_COUNTER_FILE, "w") as f:
            f.write("1")
        return 1

    with open(TICKET_COUNTER_FILE, "r+") as f:
        n = int(f.read())
        f.seek(0)
        f.write(str(n + 1))
        f.truncate()
    return n

# ======================
# BOT SETUP
# ======================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# TICKETS
# ======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green, custom_id="ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, _):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        support = guild.get_role(SUPPORT_ROLE_ID)

        number = get_next_ticket_number()

        channel = await guild.create_text_channel(
            f"ticket-{number}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True),
                support: discord.PermissionOverwrite(view_channel=True),
            }
        )

        await channel.send(
            f"🎟️ **Ticket #{number}**\n👤 {interaction.user.mention}\n🛠️ {support.mention}",
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket criado: {channel.mention}", ephemeral=True
        )

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.red, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, _):
        channel = interaction.channel
        ticket_number = channel.name.replace("ticket-", "")

        lines = []
        async for m in channel.history(limit=None, oldest_first=True):
            if m.content:
                time = m.created_at.strftime("%H:%M")
                lines.append(f"{m.author.display_name} — {time}\n{m.content}\n")

        transcript = "\n".join(lines)

        try:
            await interaction.user.send(
                f"📄 **Transcrição Ticket #{ticket_number}**\n```{transcript[:1900]}```"
            )
        except:
            pass

        await channel.delete()

@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())

    channel = bot.get_channel(CHANNEL_BUTTON_ID)
    if channel:
        await channel.purge(limit=5)
        await channel.send(
            "🎫 **Clique no botão abaixo para abrir um ticket**",
            view=TicketView()
        )

# ======================
# START
# ======================
threading.Thread(target=run_api).start()
bot.run(TOKEN)
