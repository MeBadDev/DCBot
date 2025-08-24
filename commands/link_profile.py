import json
import os
import discord
from discord import app_commands
from discord.ext import commands

async def link_profile(interaction: discord.Interaction, minecraft_username: str, linked_profiles, LINKED_PROFILES_FILE):
    # Ensure the /saved directory exists
    os.makedirs(os.path.dirname(LINKED_PROFILES_FILE), exist_ok=True)
    linked_profiles[str(interaction.user.id)] = minecraft_username
    with open(LINKED_PROFILES_FILE, 'w') as f:
        json.dump(linked_profiles, f, indent=4)
    await interaction.response.send_message(
        f"Successfully linked your profile to Minecraft username `{minecraft_username}`.", ephemeral=True
    )
    print(f"[LINK] {interaction.user} linked to Minecraft username '{minecraft_username}'.")
