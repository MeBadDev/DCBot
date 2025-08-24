


# ...existing code...

# Register reload_bot command after bot is defined
@bot.tree.command(name='reload_bot', description='Reload the bot process')
async def reload_bot_command(interaction: discord.Interaction):
    await reload_bot_cmd(interaction)


import os
import json
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from mcnet.server_scanner import scan_servers
from dotenv import load_dotenv


import yaml

CONFIG_FILE = 'config.yml'
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        config_yml = yaml.safe_load(f)
else:
    config_yml = {}
ENABLE_LOGS = config_yml.get('ENABLE_LOGS', True)
ENABLE_COMMANDS = config_yml.get('ENABLE_COMMANDS', True)
ENABLE_COMMAND_REPLACEMENT = config_yml.get('ENABLE_COMMAND_REPLACEMENT', True)

server_processes = {}
command_channels = {}
linked_profiles = {}

# Load scan folders from server_location.json
with open('server_location.json', 'r') as f:
    config = json.load(f)


scan_folders = config.get("scan_folders", [])
servers = scan_servers(scan_folders)
print(f"[INFO] Detected servers: {servers}")

bot = commands.Bot(command_prefix='/', intents=intents)

bot = commands.Bot(command_prefix='/', intents=intents)

# Register reload_bot command after bot is defined
from commands.reload_bot import reload_bot as reload_bot_cmd
@bot.tree.command(name='reload_bot', description='Reload the bot process')
async def reload_bot_command(interaction: discord.Interaction):
    await reload_bot_cmd(interaction)

# File to store linked profiles
LINKED_PROFILES_FILE = os.path.join('saved', 'linked_profiles.json')

# Load existing linked profiles from file
try:
    with open(LINKED_PROFILES_FILE, 'r') as f:
        linked_profiles = json.load(f)
except FileNotFoundError:
    linked_profiles = {}

async def broadcast_log(channel, process):
    """Broadcast server logs to the log channel."""
    log_buffer = []
    log_message = None
    last_sent = ""
    repeat_count = 0
    last_unique = ""
    while True:
        try:
            # Read lines for 5 seconds or until process ends
            for _ in range(50):  # up to 50 lines per batch
                line = await asyncio.wait_for(process.stdout.readline(), timeout=0.1)
                if not line:
                    break
                log_buffer.append(line.decode(errors='ignore').rstrip())
        except asyncio.TimeoutError:
            pass
        except Exception:
            break

        if not log_buffer and process.stdout.at_eof():
            break

        if log_buffer:
            # Prepare message
            joined = '\n'.join(log_buffer)[-1900:]
            log_buffer.clear()
            # Check for repeat
            if joined == last_sent:
                repeat_count += 1
                display = f'{joined}\n[...repeated {repeat_count} times]'
            else:
                repeat_count = 0
                display = joined
                last_unique = joined
            last_sent = joined
            if log_message is None:
                log_message = await channel.send(f'```{display}```')
            else:
                try:
                    await log_message.edit(content=f'```{display}```')
                except Exception:
                    pass
        await asyncio.sleep(5)

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')


from commands.list_servers import list_servers as list_servers_cmd
@bot.tree.command(name='list_servers', description='List all available Minecraft servers')
async def list_servers(interaction: discord.Interaction):
    await list_servers_cmd(interaction, servers)

from commands.start_server import start_server as start_server_cmd
@bot.tree.command(name='start_server', description='Start a Minecraft server by name')
@app_commands.describe(server_name='Name of the server to start')
async def start_server(interaction: discord.Interaction, server_name: str):
    await start_server_cmd(interaction, server_name, servers, server_processes, command_channels, bot, broadcast_log)

from commands.stop_server import stop_server as stop_server_cmd
@bot.tree.command(name='stop_server', description='Stop a running Minecraft server by name')
@app_commands.describe(server_name='Name of the server to stop')
async def stop_server(interaction: discord.Interaction, server_name: str):
    await stop_server_cmd(interaction, server_name, server_processes, command_channels, bot)

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
                command = message.content
                admin_user_id = os.getenv('ADMIN_USER_ID')
                # If ENABLE_COMMAND_REPLACEMENT is on, and a non-admin user targets the admin, replace target with sender
                if ENABLE_COMMAND_REPLACEMENT and admin_user_id and str(message.author.id) != admin_user_id:
                    admin_mention = f'<@{admin_user_id}>'
                    sender_mention = f'<@{message.author.id}>'
                    if admin_user_id in command or admin_mention in command:
                        command = command.replace(admin_user_id, str(message.author.id)).replace(admin_mention, sender_mention)

                # Replace mentions with linked Minecraft usernames
                import re
                mention_pattern = r'<@!?([0-9]+)>'
                failed = False
                def replace_mention(match):
                    user_id = match.group(1)
                    mc_name = linked_profiles.get(user_id)
                    if mc_name:
                        return mc_name
                    else:
                        nonlocal failed
                        failed = True
                        return match.group(0)
                command_new = re.sub(mention_pattern, replace_mention, command)
                if failed:
                    await message.add_reaction('❌')
                    return

                # Log command execution
                print(f"[COMMAND] {message.author} executed '{command_new}' on server '{server_name}'.")
                proc.stdin.write((command_new + '\n').encode())
                await proc.stdin.drain()
                await message.add_reaction('✅')
            except Exception:
                await message.add_reaction('❌')
    await bot.process_commands(message)

from commands.kill_bot import kill_bot as kill_bot_cmd
@bot.tree.command(name='kill_bot', description='Kill the bot and stop all servers (Admin only)')
async def kill_bot(interaction: discord.Interaction):
    await kill_bot_cmd(interaction, server_processes, command_channels, bot)

from commands.link_profile import link_profile as link_profile_cmd
@bot.tree.command(name='link_profile', description='Link your Discord profile to a Minecraft username')
@app_commands.describe(minecraft_username='Your Minecraft username')
async def link_profile(interaction: discord.Interaction, minecraft_username: str):
    await link_profile_cmd(interaction, minecraft_username, linked_profiles, LINKED_PROFILES_FILE)

from commands.create_server import create_server as create_server_cmd
@bot.tree.command(name='create_server', description='Create a new Minecraft server')
@app_commands.describe(name='Server name', version='Minecraft version', world='Optional world folder path')
async def create_server(interaction: discord.Interaction, name: str, version: str, world: str = None):
    await create_server_cmd(interaction, name, version, world)
    # Reload server list after server creation
    global servers
    servers = scan_servers(scan_folders)
    print(f"[INFO] Reloaded servers: {servers}")

if __name__ == '__main__':
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise RuntimeError('DISCORD_TOKEN not set in environment')
    bot.run(TOKEN)
