import discord
from discord.ext import commands
import os
import asyncio
import threading
from fastapi import FastAPI, Request
import uvicorn

# ======================
# CONFIGURAÇÕES
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID_ENV = os.getenv("DISCORD_GUILD_ID")
if not GUILD_ID_ENV:
    raise Exception("DISCORD_GUILD_ID não configurado no Railway")
GUILD_ID = int(GUILD_ID_ENV)

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

    # executa no loop do Discord (anti-crash)
    bot.loop.create_task(apply_role(discord_id, role_id, action))

    return {"status": "ok", "action": action}

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))

# ======================
# FUNÇÃO CONTADOR
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
# VIEW ABRIR TICKET (PERSISTENTE)
# ======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Abrir Ticket",
        style=discord.ButtonStyle.green,
        custom_id="ticket_open"
    )
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
            f"🎟️ **Ticket #{number}**\n"
            f"👤 {interaction.user.mention}\n"
            f"🛠️ {support.mention}",
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket criado: {channel.mention}", ephemeral=True
        )

# ======================
# VIEW FECHAR TICKET (PERSISTENTE)
# ======================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Fechar Ticket",
        style=discord.ButtonStyle.red,
        custom_id="ticket_close"
    )
    async def close_ticket(self, interaction: discord.Interaction, _):
        channel = interaction.channel
        ticket_number = channel.name.replace("ticket-", "")

        lines = []
        async for m in channel.history(limit=None, oldest_first=True):
            if not m.content:
                continue
            time = m.created_at.strftime("%H:%M")
            lines.append(
                f"👤 {m.author.display_name} — {time}\n{m.content}\n"
            )

        transcript = "\n".join(lines)

        try:
            await interaction.user.send(
                f"📄 **Transcrição Ticket #{ticket_number}**\n\n```{transcript[:1900]}```"
            )
        except:
            pass

        await channel.delete()

# ======================
# BOT READY
# ======================
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
