import discord
from discord.ext import commands
import os
from datetime import datetime
from fastapi import FastAPI, Request
import uvicorn
import asyncio
import threading

# ======================
# CONFIGURAÇÕES DISCORD
# ======================
CATEGORY_ID = 1468013305204445250
CHANNEL_BUTTON_ID = 1468013455712714873
SUPPORT_ROLE_ID = 1468012075551948944

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))  # coloque no Railway

TICKET_COUNTER_FILE = "ticket_counter.txt"

ROLE_MAP = {
    "bronze": 1468740290658566276,
    "prata": 1467901642195337380,
    "prata2": 1467901956021555311,
    "ouro": 1467902182979407912,
    "elite": 1467902327036969159,
    "expansao": 1467902455659364414
}

# ======================
# FASTAPI
# ======================
app = FastAPI()

@app.post("/discord/webhook")
async def discord_webhook(req: Request):
    data = await req.json()

    discord_id = int(data.get("discord_id"))
    plano = data.get("plano")
    acao = data.get("acao", "add")

    role_id = ROLE_MAP.get(plano)
    if not role_id:
        return {"error": "Plano inválido"}

    guild = bot.get_guild(GUILD_ID)
    member = guild.get_member(discord_id)
    role = guild.get_role(role_id)

    if not member or not role:
        return {"error": "Usuário ou cargo não encontrado"}

    if acao == "add":
        await member.add_roles(role)
    elif acao == "remove":
        await member.remove_roles(role)

    return {"status": "ok"}

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
        number = int(f.read())
        f.seek(0)
        f.write(str(number + 1))
        f.truncate()
    return number

# ======================
# BOT SETUP
# ======================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# VIEW ABRIR TICKET
# ======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green)
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        support_role = guild.get_role(SUPPORT_ROLE_ID)

        ticket_number = get_next_ticket_number()
        channel_name = f"ticket-{ticket_number}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            support_role: discord.PermissionOverwrite(view_channel=True),
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        await channel.send(
            f"🎟️ **Ticket #{ticket_number} aberto**\n"
            f"👤 {interaction.user.mention}\n"
            f"🛠️ {support_role.mention}",
            view=CloseTicketView(interaction.user.id, ticket_number)
        )

        await interaction.response.send_message(
            f"Ticket criado: {channel.mention}", ephemeral=True
        )

# ======================
# VIEW FECHAR TICKET
# ======================
class CloseTicketView(discord.ui.View):
    def __init__(self, user_id, ticket_number):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.ticket_number = ticket_number

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.red)
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):

        messages = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            messages.append(f"[{msg.created_at}] {msg.author}: {msg.content}")

        transcript = "\n".join(messages)
        user = interaction.guild.get_member(self.user_id)

        if user:
            await user.send(f"📄 Ticket #{self.ticket_number}\n```{transcript[:1900]}```")

        await interaction.channel.delete()

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    bot.add_view(TicketView())

    channel = bot.get_channel(CHANNEL_BUTTON_ID)
    if channel:
        await channel.purge(limit=5)
        await channel.send("🎫 Abra um ticket:", view=TicketView())

# ======================
# START
# ======================
threading.Thread(target=run_api).start()
bot.run(TOKEN)
