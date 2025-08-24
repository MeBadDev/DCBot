import discord
from discord import app_commands
from discord.ext import commands
import os
import sys

async def reload_bot(interaction: discord.Interaction):
    await interaction.response.send_message("Reloading bot...", ephemeral=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os.execv(sys.executable, [sys.executable] + sys.argv)
