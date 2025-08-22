server_processes = {}
command_channels = {}

import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio
import subprocess

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_API_TOKEN')

# Load server locations from JSON file
with open('server_location.json', 'r') as f:
    servers = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix='/', intents=intents)

async def broadcast_log(channel, process):
    """Broadcast server logs to the log channel."""
    log_content = ''
    log_message = None
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        log_content += line.decode(errors='ignore')
        if log_message is None:
            log_message = await channel.send(f'```{log_content[-1900:]}```')
        else:
            try:
                await log_message.edit(content=f'```{log_content[-1900:]}```')
            except Exception:
                pass

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')


@bot.tree.command(name='list_servers', description='List all available Minecraft servers')
async def list_servers(interaction: discord.Interaction):
    server_names = list(servers.keys())
    if not server_names:
        await interaction.response.send_message('No servers found.', ephemeral=True)
        return
    msg = '**Available Servers:**\n' + '\n'.join(f'- `{name}`' for name in server_names)
    await interaction.response.send_message(msg, ephemeral=True)



@bot.tree.command(name='start_server', description='Start a Minecraft server by name')
@app_commands.describe(server_name='Name of the server to start')
async def start_server(interaction: discord.Interaction, server_name: str):
    if server_name not in servers:
        await interaction.response.send_message(f'Server `{server_name}` not found.', ephemeral=True)
        return
    if server_name in server_processes:
        await interaction.response.send_message(f'Server `{server_name}` is already running.', ephemeral=True)
        return

    server = servers[server_name]
    # Log server start event
    print(f"[EVENT] {interaction.user} started server '{server_name}'.")

    # Create or get the log channel
    guild = interaction.guild
    log_channel_name = 'log'
    old_log_channel = discord.utils.get(guild.text_channels, name=log_channel_name)
    if old_log_channel:
        await old_log_channel.delete()
    log_channel = await guild.create_text_channel(log_channel_name)

    # Create or get the command channel
    command_channel_name = f'{server_name.lower()}-commands'
    old_command_channel = discord.utils.get(guild.text_channels, name=command_channel_name)
    if old_command_channel:
        await old_command_channel.delete()
    command_channel = await guild.create_text_channel(command_channel_name)

    await interaction.response.send_message(f'Starting server `{server_name}`... Logs will be sent to {log_channel.mention} and commands can be sent to {command_channel.mention}.')

    # Start the server process in its own directory
    server_path = server['path']
    server_dir = os.path.dirname(server_path)
    proc = await asyncio.create_subprocess_exec(
        'java', '-jar', server_path, 'nogui',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        stdin=asyncio.subprocess.PIPE,  # Ensure stdin is enabled
        cwd=server_dir
    )
    server_processes[server_name] = proc
    command_channels[command_channel.id] = server_name

    # Broadcast logs to the log channel
    bot.loop.create_task(broadcast_log(log_channel, proc))

@bot.tree.command(name='stop_server', description='Stop a running Minecraft server by name')
@app_commands.describe(server_name='Name of the server to stop')
async def stop_server(interaction: discord.Interaction, server_name: str):
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
    # Optionally, clean up references after a delay
    async def cleanup():
        await asyncio.sleep(5)
        server_processes.pop(server_name, None)
        # Remove command channel mapping(s) for this server
        to_remove = [cid for cid, sname in command_channels.items() if sname == server_name]
        for cid in to_remove:
            command_channels.pop(cid, None)
    bot.loop.create_task(cleanup())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id in command_channels:
        print("Received command for server: ", command_channels[message.channel.id])
        server_name = command_channels[message.channel.id]
        proc = server_processes.get(server_name)
        
        if proc and proc.stdin:
            try:
                # Log command execution
                print(f"[COMMAND] {message.author} executed '{message.content}' on server '{server_name}'.")
                proc.stdin.write((message.content + '\n').encode())
                await proc.stdin.drain()
                await message.add_reaction('✅')
            except Exception:
                await message.add_reaction('❌')
    await bot.process_commands(message)

@bot.tree.command(name='kill_bot', description='Kill the bot and stop all servers (Admin only)')
async def kill_bot(interaction: discord.Interaction):
    admin_user_id = os.getenv('ADMIN_USER_ID')
    if str(interaction.user.id) != admin_user_id:
        await interaction.response.send_message('You do not have permission to kill the bot.', ephemeral=True)
        return

    await interaction.response.send_message('Shutting down the bot and stopping all servers...')
    print(f"[ADMIN] {interaction.user} issued bot shutdown.")

    # Gracefully stop all running servers
    for server_name, proc in server_processes.items():
        if proc and proc.stdin:
            try:
                print(f"[SHUTDOWN] Stopping server '{server_name}'.")
                proc.stdin.write(b'stop\n')
                await proc.stdin.drain()
            except Exception as e:
                print(f"[ERROR] Failed to stop server '{server_name}': {e}")

    # Clear server processes and command channels
    server_processes.clear()
    command_channels.clear()

    # Shutdown the bot
    await bot.close()

if __name__ == '__main__':
    bot.run(TOKEN)
