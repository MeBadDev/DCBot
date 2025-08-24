import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json

async def create_server(interaction: discord.Interaction, name: str, version: str, world: str = None):
    await interaction.response.defer(thinking=True)
    import aiohttp
    import zipfile
    import tempfile
    import cloudscraper
    import concurrent.futures
    # Fetch version manifest
    async with aiohttp.ClientSession() as session:
        async with session.get('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json') as resp:
            manifest = await resp.json()
    # Find version info
    version_info = next((v for v in manifest['versions'] if v['id'] == version), None)
    if not version_info:
        await interaction.followup.send(f"Version `{version}` not found.", ephemeral=True)
        return
    # Fetch version details
    async with aiohttp.ClientSession() as session:
        async with session.get(version_info['url']) as resp:
            version_json = await resp.json()
    server_url = version_json.get('downloads', {}).get('server', {}).get('url')
    if not server_url:
        await interaction.followup.send(f"No server jar found for version `{version}`.", ephemeral=True)
        return
    # Prepare server directory
    # Always use the first scan_folders entry from server_location.json
    with open('server_location.json', 'r') as f:
        config = json.load(f)
    scan_folders = config.get('scan_folders', [])
    if not scan_folders:
        await interaction.followup.send('No scan_folders configured in server_location.json.', ephemeral=True)
        return
    servers_root = scan_folders[0]
    server_dir = os.path.join(servers_root, name)
    os.makedirs(server_dir, exist_ok=True)
    jar_path = os.path.join(server_dir, 'server.jar')
    # Download server jar
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(server_url) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    await interaction.followup.send(f"Failed to download server jar. HTTP {resp.status}: {text[:200]}", ephemeral=True)
                    return
                with open(jar_path, 'wb') as f:
                    while True:
                        chunk = await resp.content.read(1024*1024)
                        if not chunk:
                            break
                        f.write(chunk)
        except Exception as e:
            await interaction.followup.send(f"Exception while downloading server jar: {e}", ephemeral=True)
            return
    # Optionally download and extract world from URL
    if world:
        import shutil
        try:
            # Use cloudscraper in a thread to download the world file (Cloudflare bypass)
            loop = asyncio.get_running_loop()
            def download_world():
                scraper = cloudscraper.create_scraper(interpreter='js2py')
                resp = scraper.get(world, stream=True)
                return resp
            try:
                resp = await loop.run_in_executor(None, download_world)
            except Exception as e:
                await interaction.followup.send(f"Exception while downloading world: {e}", ephemeral=True)
                return
            if resp.status_code != 200:
                await interaction.followup.send(f"Failed to download world from URL. HTTP {resp.status_code}: {resp.text[:200]}", ephemeral=True)
                return
            with tempfile.NamedTemporaryFile(delete=False) as tmpf:
                for chunk in resp.iter_content(chunk_size=1024*1024):
                    if not chunk:
                        break
                    tmpf.write(chunk)
                tmpf_path = tmpf.name
            # Try to extract zip and handle both cases
            world_dir = os.path.join(server_dir, 'world')
            os.makedirs(world_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(tmpf_path, 'r') as zip_ref:
                    top_level = set()
                    for member in zip_ref.namelist():
                        if member.strip():
                            top = member.split('/')[0]
                            if top:
                                top_level.add(top)
                    # Case 1: single top-level folder
                    if len(top_level) == 1:
                        temp_extract = tempfile.mkdtemp()
                        zip_ref.extractall(temp_extract)
                        # Find the actual world folder inside
                        extracted_root = os.path.join(temp_extract, list(top_level)[0])
                        # Move/copy all contents to world_dir
                        for item in os.listdir(extracted_root):
                            s = os.path.join(extracted_root, item)
                            d = os.path.join(world_dir, item)
                            if os.path.isdir(s):
                                shutil.copytree(s, d, dirs_exist_ok=True)
                            else:
                                shutil.copy2(s, d)
                        shutil.rmtree(temp_extract)
                    else:
                        # Case 2: flat zip, extract all to world_dir
                        zip_ref.extractall(world_dir)
            except Exception as e:
                await interaction.followup.send(f"Downloaded world is not a valid zip: {e}", ephemeral=True)
                return
            finally:
                os.remove(tmpf_path)
        except Exception as e:
            await interaction.followup.send(f"Failed to download or extract world: {e}", ephemeral=True)
            return
    # Write eula.txt after server creation
    import datetime
    eula_path = os.path.join(server_dir, 'eula.txt')
    now = datetime.datetime.now().strftime('%a %b %d %H:%M:%S CST %Y')
    with open(eula_path, 'w', encoding='utf-8') as f:
        f.write(f"#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
        f.write(f"#{now}\n")
        f.write("eula=true\n")
    await interaction.followup.send(f"Server `{name}` created for version `{version}`. Now configure server properties:",
                                   view=ServerPropertiesView(server_dir))


# --- UI for server properties ---
import discord
class ServerPropertiesView(discord.ui.View):
    def __init__(self, server_dir):
        super().__init__(timeout=300)
        self.server_dir = server_dir
        self.add_item(CommandBlockSelect())
        self.add_item(OnlineModeSelect())
        self.add_item(MaxPlayersSelect())
        self.add_item(MOTDButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the user who created the server to interact
        return True

class CommandBlockSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Allow Command Blocks", value="true", description="Enable command blocks"),
            discord.SelectOption(label="Disallow Command Blocks", value="false", description="Disable command blocks"),
        ]
        super().__init__(placeholder="Allow command blocks?", min_values=1, max_values=1, options=options, custom_id="cmdblock")

    async def callback(self, interaction: discord.Interaction):
        view: ServerPropertiesView = self.view
        update_server_property(view.server_dir, "enable-command-block", self.values[0])
        await interaction.response.send_message(f"Set enable-command-block to {self.values[0]}", ephemeral=True)

class OnlineModeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Online Mode (Auth on)", value="true", description="Require Mojang auth"),
            discord.SelectOption(label="Offline Mode (Auth off)", value="false", description="No Mojang auth"),
        ]
        super().__init__(placeholder="Online mode?", min_values=1, max_values=1, options=options, custom_id="onlinemode")

    async def callback(self, interaction: discord.Interaction):
        view: ServerPropertiesView = self.view
        update_server_property(view.server_dir, "online-mode", self.values[0])
        await interaction.response.send_message(f"Set online-mode to {self.values[0]}", ephemeral=True)

class MaxPlayersSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="10 Players", value="10"),
            discord.SelectOption(label="20 Players", value="20"),
            discord.SelectOption(label="50 Players", value="50"),
            discord.SelectOption(label="100 Players", value="100"),
        ]
        super().__init__(placeholder="Max players?", min_values=1, max_values=1, options=options, custom_id="maxplayers")

    async def callback(self, interaction: discord.Interaction):
        view: ServerPropertiesView = self.view
        update_server_property(view.server_dir, "max-players", self.values[0])
        await interaction.response.send_message(f"Set max-players to {self.values[0]}", ephemeral=True)

class MOTDButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Set MOTD", style=discord.ButtonStyle.primary, custom_id="motd")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MOTDModal(self.view.server_dir))

class MOTDModal(discord.ui.Modal, title="Set MOTD"):
    motd = discord.ui.TextInput(label="MOTD", style=discord.TextStyle.short, required=True, max_length=60)

    def __init__(self, server_dir):
        super().__init__()
        self.server_dir = server_dir

    async def on_submit(self, interaction: discord.Interaction):
        update_server_property(self.server_dir, "motd", self.motd.value)
        await interaction.response.send_message(f"Set MOTD to: {self.motd.value}", ephemeral=True)

def update_server_property(server_dir, key, value):
    prop_path = os.path.join(server_dir, "server.properties")
    lines = []
    found = False
    if os.path.exists(prop_path):
        with open(prop_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(prop_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
