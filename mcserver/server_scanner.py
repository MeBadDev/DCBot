
import os
import json
import zipfile

def scan_servers(scan_folders):
    servers = {}
    for folder in scan_folders:
        if os.path.exists(folder):
            for server_name in os.listdir(folder):
                server_path = os.path.join(folder, server_name)
                if os.path.isdir(server_path):
                    jar_files = [f for f in os.listdir(server_path) if f.endswith('.jar')]
                    if jar_files:
                        jar_path = os.path.join(server_path, jar_files[0])
                        version_id = "Unknown"
                        try:
                            with zipfile.ZipFile(jar_path, "r") as jar:
                                with jar.open("version.json") as f:
                                    data = json.load(f)
                                    version_id = data.get("id", "Unknown")
                        except Exception as e:
                            print(f"[WARN] Could not extract version from {jar_path}: {e}")
                        servers[server_name] = {
                            "version": version_id,
                            "path": jar_path
                        }
    return servers
