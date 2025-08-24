# Discord Minecraft Server Bot

This bot allows you to manage a Minecraft server directly from Discord. It supports starting and stopping servers, executing commands, and logging events.
[!CAUTION]
> it's also hacked together in 40 minutes so I don't recommend it for production/real world use!

## Features
- Start a Minecraft server with `/start_server [server_name]`.
- Stop a running server with `/stop_server [server_name]`.
- Execute commands in a dedicated channel for each server.
> [!IMPORTANT]
> **ANYONE** with 'send message' permission will be able to send command to the server!
- Log server events and commands to a log channel.
- Admin-only `/kill_bot` command to gracefully stop all servers and shut down the bot.

## Setup

### Prerequisites
- Python 3.8 or higher
- `pip` (Python package manager)
- Java installed on the server machine

### Installation
1. Clone this repository or download the source code.
2. Navigate to the project directory:
   ```bash
   cd DCBot
   ```
3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On macOS/Linux
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Configure the `.env` file:
   - Add your Discord bot token as `DISCORD_API_TOKEN`.
   - Add the `ADMIN_USER_ID` for the user allowed to shut down the bot.
   - Example:
     ```env
     DISCORD_API_TOKEN=your_discord_token_here
     ADMIN_USER_ID=12345678901234578
         ```
6. Define your Minecraft servers in `server_location.json`:
   ```json
   {
       "Oneblock": {
           "version": "1.21.8",
           "name": "Oneblock",
           "path": "C:\\Users\\MeBadDev\\Documents\\MCServer\\server.jar"
       }
   }
   ```

### Running the Bot
To start the bot, run:
```bash
python bot.py
```

### Packaging the Bot
To package the bot into an executable:
1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Create the executable:
   ```bash
   pyinstaller --onefile --noconsole --name "MCServer" bot.py
   ```
3. The executable will be located in the `dist` folder.

## Commands
- `/start_server [server_name]`: Start a Minecraft server.
- `/stop_server [server_name]`: Stop a running server.
- `/kill_bot`: Admin-only command to stop all servers and shut down the bot.

## License
This project is licensed under the MIT License.
