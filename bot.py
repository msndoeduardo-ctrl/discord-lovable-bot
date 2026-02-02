import discord
from discord.ext import commands
import os
from datetime import datetime

# ======================
# CONFIGURAÇÕES
# ======================
CATEGORY_ID = 1468013305204445250
CHANNEL_BUTTON_ID = 1468013455712714873
SUPPORT_ROLE_ID = 1468012075551948944

TOKEN = os.getenv("DISCORD_TOKEN")

TICKET_COUNTER_FILE = "ticket_counter.txt"

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

    @discord.ui.button(
        label="🎫 Abrir Ticket",
        style=discord.ButtonStyle.green,
        custom_id="abrir_ticket"
    )
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        support_role = guild.get_role(SUPPORT_ROLE_ID)

        ticket_number = get_next_ticket_number()
        channel_name = f"ticket-{ticket_number}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        await ticket_channel.send(
            f"🎟️ **Ticket #{ticket_number} aberto**\n\n"
            f"👤 Cliente: {interaction.user.mention}\n"
            f"🛠️ Suporte: {support_role.mention}",
            view=CloseTicketView(interaction.user.id, ticket_number)
        )

        await interaction.response.send_message(
            f"✅ Ticket criado: {ticket_channel.mention}",
            ephemeral=True
        )

# ======================
# VIEW FECHAR TICKET
# ======================
class CloseTicketView(discord.ui.View):
    def __init__(self, user_id: int, ticket_number: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.ticket_number = ticket_number

    @discord.ui.button(
        label="🔒 Fechar Ticket",
        style=discord.ButtonStyle.red,
        custom_id="fechar_ticket"
    )
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(ephemeral=True)

        messages = []
        async for message in interaction.channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%d/%m/%Y %H:%M")
            messages.append(f"[{timestamp}] {message.author}: {message.content}")

        transcript = "\n".join(messages)

        user = interaction.guild.get_member(self.user_id)

        if user:
            try:
                await user.send(
                    f"📄 **Transcrição do Ticket #{self.ticket_number}**\n\n```{transcript[:1900]}```"
                )
            except:
                pass

        await interaction.channel.delete()

# ======================
# BOT READY
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")

    bot.add_view(TicketView())

    channel = bot.get_channel(CHANNEL_BUTTON_ID)
    if channel:
        await channel.purge(limit=10)
        await channel.send(
            "🎫 **Clique no botão abaixo para abrir um ticket**",
            view=TicketView()
        )

# ======================
# RUN
# ======================
bot.run(TOKEN)
