import asyncio
import discord
from discord import app_commands
from discord.ext import commands

async def stop_server(interaction: discord.Interaction, server_name: str, server_processes, command_channels, bot):
    proc = server_processes.get(server_name)
    if not proc or not proc.stdin:
        await interaction.response.send_message(f'Server `{server_name}` is not running.', ephemeral=True)
        return
    try:
        proc.stdin.write(b'stop\n')
        await proc.stdin.drain()
        await interaction.response.send_message(f'Sent stop command to `{server_name}`.')
    except Exception as e:
        await interaction.response.send_message(f'Failed to stop `{server_name}`: {e}', ephemeral=True)
    async def cleanup():
        await asyncio.sleep(5)
        server_processes.pop(server_name, None)
        to_remove = [cid for cid, sname in command_channels.items() if sname == server_name]
        for cid in to_remove:
            command_channels.pop(cid, None)
    bot.loop.create_task(cleanup())
