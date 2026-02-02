import discord
from discord.ext import commands
from flask import Flask
import threading
import os

TOKEN = os.getenv("DISCORD_TOKEN")

# ===== CONFIG =====
CATEGORY_ID = 123456789012345678  # ID da categoria de tickets
SUPPORT_ROLE_ID = 123456789012345678  # ID do cargo Suporte
# ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== FLASK =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Discord rodando"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_flask).start()
# =================

# ===== BOT READY =====
@bot.event
async def on_ready():
    print(f"🤖 Conectado como {bot.user}")
# =====================

# ===== VIEW BOTÃO =====
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ Abrir Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)
        support_role = guild.get_role(SUPPORT_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        await channel.send(
            f"{support_role.mention} 🎫 Ticket criado por {interaction.user.mention}",
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            "✅ Seu ticket foi criado!",
            ephemeral=True
        )

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# =====================

# ===== COMANDO PARA ENVIAR O BOTÃO =====
@bot.command()
@commands.has_permissions(administrator=True)
async def painel(ctx):
    embed = discord.Embed(
        title="🎟️ Central de Atendimento",
        description="Clique no botão abaixo para abrir um ticket.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=TicketView())
# =====================

bot.run(TOKEN)
