import discord
from discord.ext import commands
import os
import asyncio
from fastapi import FastAPI, Request
import uvicorn
import threading

# ======================
# CONFIG
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

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
# BOT
# ======================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# FASTAPI
# ======================
app = FastAPI()

async def apply_role(discord_id: int, role_id: int, action: str):
    guild = bot.get_guild(GUILD_ID)
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

    discord_id = int(data["discord_id"])
    plano = data["plano"]
    action = data.get("acao", "add")

    role_id = ROLE_MAP.get(plano)
    if not role_id:
        return {"error": "Plano inválido"}

    # executa no loop do discord (ANTI-CRASH)
    bot.loop.create_task(apply_role(discord_id, role_id, action))

    return {"status": "ok", "action": action}

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))

# ======================
# TICKET COUNTER
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
# VIEWS
# ======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green)
    async def open(self, interaction: discord.Interaction, _):
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
            view=CloseTicketView(interaction.user.id, number)
        )

        await interaction.response.send_message(
            f"Ticket criado: {channel.mention}", ephemeral=True
        )

class CloseTicketView(discord.ui.View):
    def __init__(self, user_id, ticket_number):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.ticket_number = ticket_number

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, _):
        lines = []
        async for m in interaction.channel.history(limit=None, oldest_first=True):
            if not m.content:
                continue
            time = m.created_at.strftime("%H:%M")
            lines.append(f"👤 **{m.author.display_name}** — {time}\n{m.content}\n")

        transcript = "\n".join(lines)
        user = interaction.guild.get_member(self.user_id)

        if user:
            await user.send(
                f"📄 **Transcrição Ticket #{self.ticket_number}**\n\n```{transcript[:1900]}```"
            )

        await interaction.channel.delete()

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    bot.add_view(TicketView())

    ch = bot.get_channel(CHANNEL_BUTTON_ID)
    if ch:
        await ch.purge(limit=5)
        await ch.send("🎫 Clique para abrir um ticket:", view=TicketView())

# ======================
# START
# ======================
threading.Thread(target=run_api).start()
bot.run(TOKEN)
