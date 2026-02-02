import discord
from discord.ext import commands
from discord import app_commands
import os

# ======================
# CONFIGURAÇÕES
# ======================
CATEGORY_ID = 1468013305204445250
CHANNEL_BUTTON_ID = 1468013455712714873
SUPPORT_ROLE_ID = 1468012075551948944

TOKEN = os.getenv("DISCORD_TOKEN")

# ======================
# BOT SETUP
# ======================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# VIEW DO BOTÃO
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

        # Nome do canal
        channel_name = f"ticket-{interaction.user.name}".lower()

        # Evita ticket duplicado
        for channel in category.channels:
            if interaction.user.name.lower() in channel.name:
                await interaction.response.send_message(
                    "❌ Você já tem um ticket aberto.",
                    ephemeral=True
                )
                return

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
            f"🎟️ **Ticket aberto!**\n\n"
            f"{interaction.user.mention}, descreva seu problema.\n"
            f"{support_role.mention} foi acionado."
        )

        await interaction.response.send_message(
            f"✅ Ticket criado: {ticket_channel.mention}",
            ephemeral=True
        )

# ======================
# BOT READY
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"🔄 Slash commands sincronizados ({len(synced)})")
    except Exception as e:
        print(e)

    bot.add_view(TicketView())

    channel = bot.get_channel(CHANNEL_BUTTON_ID)
    if channel:
        await channel.purge(limit=10)
        await channel.send(
            "🎫 **Abra um ticket clicando no botão abaixo**",
            view=TicketView()
        )

# ======================
# RUN
# ======================
bot.run(TOKEN)
