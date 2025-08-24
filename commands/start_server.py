import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

async def start_server(interaction: discord.Interaction, server_name: str, servers, server_processes, command_channels, bot, broadcast_log):
    if server_name not in servers:
        await interaction.response.send_message(f'Server `{server_name}` not found.', ephemeral=True)
        print(f"[INFO] Server: {server_name} not found!")
        print(f"[INFO] Available Servers: {list(servers.keys())}")
        return
    if server_name in server_processes:
        await interaction.response.send_message(f'Server `{server_name}` is already running.', ephemeral=True)
        return
    server = servers[server_name]
    print(f"[EVENT] {interaction.user} started server '{server_name}'.")
    guild = interaction.guild
    log_channel_name = 'log'
    old_log_channel = discord.utils.get(guild.text_channels, name=log_channel_name)
    if old_log_channel:
        await old_log_channel.delete()
    log_channel = await guild.create_text_channel(log_channel_name)
    command_channel_name = f'{server_name.lower()}-commands'
    old_command_channel = discord.utils.get(guild.text_channels, name=command_channel_name)
    if old_command_channel:
        await old_command_channel.delete()
    command_channel = await guild.create_text_channel(command_channel_name)
    await interaction.response.send_message(f'Starting server `{server_name}`... Logs will be sent to {log_channel.mention} and commands can be sent to {command_channel.mention}.')
    server_path = server['path']
    server_dir = os.path.dirname(server_path)
    proc = await asyncio.create_subprocess_exec(
        'java', '-jar', server_path, 'nogui',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        stdin=asyncio.subprocess.PIPE,
        cwd=server_dir
    )
    server_processes[server_name] = proc
    command_channels[command_channel.id] = server_name
    bot.loop.create_task(broadcast_log(log_channel, proc))
