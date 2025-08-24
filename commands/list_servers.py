import discord
from discord import app_commands
from discord.ext import commands

async def list_servers(interaction: discord.Interaction, servers):
    server_names = list(servers.keys())
    if not server_names:
        await interaction.response.send_message('No servers found.', ephemeral=True)
        return
    embed = discord.Embed(title="Available Servers", color=discord.Color.blue())
    for server_name in server_names:
        server_info = servers[server_name]
        embed.add_field(
            name=server_name,
            value=f"Version: {server_info['version']}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)
