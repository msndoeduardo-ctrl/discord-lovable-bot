import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! Online no Railway!")

# Flask pra manter vivo
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Discord rodando!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

bot.run(TOKEN)
