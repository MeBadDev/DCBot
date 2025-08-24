import os
import discord
from discord.ext import commands

async def kill_bot(interaction: discord.Interaction, server_processes, command_channels, bot):
    admin_user_id = os.getenv('ADMIN_USER_ID')
    if str(interaction.user.id) != admin_user_id:
        await interaction.response.send_message('You do not have permission to kill the bot.', ephemeral=True)
        return
    await interaction.response.send_message('Shutting down the bot and stopping all servers...')
    print(f"[ADMIN] {interaction.user} issued bot shutdown.")
    for server_name, proc in server_processes.items():
        if proc and proc.stdin:
            try:
                print(f"[SHUTDOWN] Stopping server '{server_name}'.")
                proc.stdin.write(b'stop\n')
                await proc.stdin.drain()
            except Exception as e:
                print(f"[ERROR] Failed to stop server '{server_name}': {e}")
    server_processes.clear()
    command_channels.clear()
    await bot.close()
