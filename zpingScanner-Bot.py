#!/usr/bin/env python3
"""
MCSeeker Unified Bot - Discord Bot with Integrated Minecraft Scanner
Combines Discord bot functionality with Python Minecraft scanner
"""

import os
import discord
from discord import app_commands, File
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import argparse
import csv
import fnmatch
import json
import re
import socket
import struct
import sys
import time
import urllib.request
import urllib.parse
import zipfile
import gzip
import tarfile
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import io
import shlex
from datetime import datetime
from threading import Thread
from flask import Flask

# Load environment variables
load_dotenv()

# Try to import optional dependencies
try:
    import maxminddb
    MAXMIND_AVAILABLE = True
except ImportError:
    MAXMIND_AVAILABLE = False

try:
    import mcstatus
    from mcstatus import JavaServer
    JAVA_SERVER_AVAILABLE = True
except ImportError:
    JAVA_SERVER_AVAILABLE = False

# =========================
# ⚙️ Configuration
# =========================
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

# Minecraft Scanner Constants
MINECRAFT_DEFAULT_PORT = '25565-25566'
DEFAULT_TIMEOUT = 15
DEFAULT_CONCURRENCY = 256

# =========================
# 🎯 Data Classes
# =========================
@dataclass
class ScanResult:
    ip: str
    port: int
    version: str = ""
    players_online: int = 0
    players_max: int = 0
    description: str = ""
    country: str = ""
    latitude: float = 0.0
    longitude: float = 0.0

# =========================
# 🔍 Minecraft Scanner Class
# =========================
class MinecraftScanner:
    def __init__(self, args=None):
        self.geoip_reader = None
        self.client_token = None
        
        # Default values
        self.scan_hosts = '0.0.0.0/0'
        self.scan_ports = MINECRAFT_DEFAULT_PORT
        self.min_players = 0
        self.max_players = None
        self.version_filter = '*'
        self.concurrency = DEFAULT_CONCURRENCY
        self.timeout = DEFAULT_TIMEOUT
        self.output_file = None
        self.output_format = 'csv'
        self.show_desc = False
        self.geo_ip = False
        self.geo_coords = False
        self.enable_client = False
        self.quiet = False
        self.maxmind_key = None
        
        # Override with args if provided
        if args:
            self.scan_hosts = args.get('ip', self.scan_hosts)
            self.scan_ports = args.get('port', self.scan_ports)
            self.min_players = args.get('min_players', self.min_players)
            self.max_players = args.get('max_players', self.max_players)
            self.version_filter = args.get('version', self.version_filter)
            self.concurrency = args.get('conc', self.concurrency)
            self.timeout = args.get('timeout', self.timeout)
            self.output_file = args.get('out', self.output_file)
            self.output_format = args.get('format', self.output_format)
            self.show_desc = args.get('show_desc', self.show_desc)
            self.geo_ip = args.get('geo_ip', self.geo_ip)
            self.geo_coords = args.get('geo_coords', self.geo_coords)
            self.enable_client = args.get('enable_client', self.enable_client)
            self.quiet = args.get('quiet', self.quiet)
            self.maxmind_key = args.get('maxmind_key', self.maxmind_key)
            self.client_token = args.get('client_token', self.client_token)
        
        # Validate arguments
        if self.quiet and not self.output_file:
            raise ValueError("You have asked for --quiet output, but did not specify an --out file. This scan is pointless!")
        
        # Setup GeoIP if requested
        if self.geo_ip:
            self._setup_geoip()
        
        # Setup client token if requested
        if self.enable_client and not self.client_token:
            self._get_free_token()

    def _setup_geoip(self):
        """Setup GeoIP database"""
        geoip_file = "./GeoLite2.mmdb"
        
        if not os.path.exists(geoip_file):
            if not self.maxmind_key:
                raise ValueError("NO MAXMIND DOWNLOAD KEY WAS PROVIDED! CANNOT DOWNLOAD THE DATABASE WITHOUT A KEY!")
            
            print("Downloading GeoIP database...")
            self._download_geoip_database()
        
        if MAXMIND_AVAILABLE:
            try:
                self.geoip_reader = maxminddb.open_database(geoip_file)
                print("GeoIP database loaded successfully.")
            except Exception as e:
                raise Exception(f"Error loading GeoIP database: {e}")
        else:
            raise Exception("maxminddb library not available. Install with: pip install maxminddb")

    def _download_geoip_database(self):
        """Download GeoIP database from MaxMind"""
        url = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={self.maxmind_key}&suffix=tar.gz"
        
        try:
            print("Downloading GeoIP database...")
            with urllib.request.urlopen(url) as response:
                data = response.read()
            
            # Write tar.gz file
            with open("./GeoLite2.tar.gz", "wb") as f:
                f.write(data)
            
            # Extract the database
            with tarfile.open("./GeoLite2.tar.gz", "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.mmdb'):
                        member.name = os.path.basename(member.name)  # Remove directory structure
                        tar.extract(member, path="./")
                        break
            
            # Clean up
            os.remove("./GeoLite2.tar.gz")
            print("GeoIP database downloaded and extracted successfully.")
            
        except Exception as e:
            raise Exception(f"Error downloading GeoIP database: {e}")




















    def _download_geoip_database(self):
        """Download GeoIP database from MaxMind"""
        # Tu license key de MaxMind
        license_key = "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"
        
        url = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz"
        
        try:
            print("Downloading GeoIP database...")
            with urllib.request.urlopen(url) as response:
                data = response.read()
            
            # Write tar.gz file
            with open("./GeoLite2.tar.gz", "wb") as f:
                f.write(data)
            
            # Extract the database
            with tarfile.open("./GeoLite2.tar.gz", "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.mmdb'):
                        member.name = os.path.basename(member.name)
                        tar.extract(member, path="./")
                        break
            
            # Clean up
            os.remove("./GeoLite2.tar.gz")
            print("GeoIP database downloaded and extracted successfully.")
            
        except Exception as e:
            raise Exception(f"Error downloading GeoIP database: {e}")































    def _get_free_token(self):
        """Get free token from TheAltening API"""
        try:
            with urllib.request.urlopen("https://api.thealtening.com/free/generate") as response:
                data = json.loads(response.read().decode())
                self.client_token = data.get('token')
                if self.client_token:
                    print(f"Free token obtained: {self.client_token}")
                else:
                    print("No token obtained from TheAltening API")
        except Exception as e:
            print(f"Error getting free token: {e}")

    def _parse_port_range(self, port_string: str) -> List[int]:
        """Parse port range string like '25565-25566' or '25565'"""
        ports = []
        
        for part in port_string.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                ports.extend(range(start, end + 1))
            else:
                ports.append(int(part))
        
        return ports

    def _parse_ip_range(self, ip_string: str) -> List[str]:
        """Parse IP range string"""
        # For simplicity, this handles basic cases
        # In a full implementation, you'd want to handle CIDR notation properly
        if '/' in ip_string:
            # Handle CIDR notation (simplified)
            base_ip = ip_string.split('/')[0]
            if ip_string == '0.0.0.0/0':
                # For full scan, we'll use a limited range for demo
                return ['127.0.0.1']  # Simplified for demo
            return [base_ip]
        else:
            return [ip_string]

    def _minecraft_ping(self, ip: str, port: int) -> Optional[Dict]:
        """Ping a Minecraft server"""
        try:
            if not JAVA_SERVER_AVAILABLE:
                # Fallback to manual ping implementation
                return self._manual_minecraft_ping(ip, port)
            
            server = JavaServer(ip, port)
            status = server.status()
            
            return {
                'version': status.version.name,
                'protocol': status.version.protocol,
                'players_online': status.players.online,
                'players_max': status.players.max,
                'description': status.description.get('text', '') if hasattr(status.description, 'get') else str(status.description),
                'latency': status.latency
            }
            
        except Exception as e:
            return None

    def _manual_minecraft_ping(self, ip: str, port: int) -> Optional[Dict]:
        """Manual Minecraft ping implementation"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            # Connect to server
            sock.connect((ip, port))
            
            # Send handshake packet
            packet_id = 0x00
            protocol_version = 47  # 1.8.x
            server_address = ip
            server_port = port
            next_state = 1  # Status
            
            # Build handshake packet
            data = bytearray()
            data.extend(self._write_varint(packet_id))
            data.extend(self._write_varint(protocol_version))
            data.extend(self._write_string(server_address))
            data.extend(struct.pack('>H', server_port))
            data.extend(self._write_varint(next_state))
            
            # Send packet length + packet data
            packet_length = len(data)
            sock.send(self._write_varint(packet_length) + data)
            
            # Send status request
            sock.send(self._write_varint(1) + self._write_varint(0x00))
            
            # Read response
            response_length = self._read_varint(sock)
            response_data = sock.recv(response_length)
            
            sock.close()
            
            # Parse response
            return self._parse_status_response(response_data)
            
        except Exception as e:
            return None

    def _write_varint(self, value: int) -> bytes:
        """Write a varint to bytes"""
        data = bytearray()
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                byte |= 0x80
            data.append(byte)
            if value == 0:
                break
        return bytes(data)

    def _read_varint(self, sock: socket.socket) -> int:
        """Read a varint from socket"""
        result = 0
        shift = 0
        while True:
            byte = sock.recv(1)
            if not byte:
                raise Exception("Connection closed")
            
            byte = byte[0]
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result

    def _write_string(self, string: str) -> bytes:
        """Write a string to bytes"""
        string_bytes = string.encode('utf-8')
        return self._write_varint(len(string_bytes)) + string_bytes

    def _read_string(self, data: bytearray, offset: int) -> Tuple[str, int]:
        """Read a string from bytearray"""
        length, offset = self._read_varint_from_data(data, offset)
        string_bytes = data[offset:offset + length]
        return string_bytes.decode('utf-8'), offset + length

    def _read_varint_from_data(self, data: bytearray, offset: int) -> Tuple[int, int]:
        """Read a varint from bytearray"""
        result = 0
        shift = 0
        while offset < len(data):
            byte = data[offset]
            offset += 1
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result, offset

    def _parse_status_response(self, data: bytearray) -> Optional[Dict]:
        """Parse Minecraft status response"""
        try:
            offset = 0
            
            # Skip packet ID
            _, offset = self._read_varint_from_data(data, offset)
            
            # Read JSON string
            json_string, offset = self._read_string(data, offset)
            status_data = json.loads(json_string)
            
            # Extract information
            version = status_data.get('version', {})
            players = status_data.get('players', {})
            description = status_data.get('description', {})
            
            return {
                'version': version.get('name', 'Unknown'),
                'protocol': version.get('protocol', 0),
                'players_online': players.get('online', 0),
                'players_max': players.get('max', 0),
                'description': description.get('text', '') if isinstance(description, dict) else str(description),
                'latency': 0
            }
            
        except Exception as e:
            return None

    def _get_geoip_info(self, ip: str) -> Tuple[str, float, float]:
        """Get GeoIP information for an IP"""
        if not self.geoip_reader:
            return "", 0.0, 0.0
        
        try:
            response = self.geoip_reader.get(ip)
            if response:
                country = response.get('country', {}).get('iso_code', '')
                location = response.get('location', {})
                latitude = location.get('latitude', 0.0)
                longitude = location.get('longitude', 0.0)
                return country, latitude, longitude
        except Exception:
            pass
        
        return "", 0.0, 0.0

    def _matches_version_filter(self, version: str) -> bool:
        """Check if version matches the filter"""
        return fnmatch.fnmatch(version, self.version_filter)

    def _format_description(self, description: str) -> str:
        """Format Minecraft description text"""
        # Remove color codes and format text
        text = re.sub(r'§[0-9a-fk-or]', '', description)  # Remove Minecraft color codes
        text = re.sub(r'\n', ' ', text)  # Replace newlines with spaces
        return text.strip()

    def _format_result_line(self, result: ScanResult) -> str:
        """Format result for console output"""
        the_text = f"{result.ip}:{result.port}\t{result.version}\t{result.players_online} of {result.players_max} players"
        
        if self.show_desc:
            the_text += f"\t{self._format_description(result.description)}"
        
        if self.geo_ip and result.country:
            geo_text = result.country
            if self.geo_coords:
                geo_text += f" ({result.latitude},{result.longitude})"
            the_text = f"[{geo_text}] {the_text}"
        
        return the_text

    def _format_csv_row(self, result: ScanResult) -> List[str]:
        """Format result for CSV output"""
        row = [f"{result.ip}:{result.port}", 
               result.version.replace(',', '+'),
               f"{result.players_online}/{result.players_max}"]
        
        if self.show_desc:
            row.append(self._format_description(result.description).replace(',', ';'))
        
        if self.geo_ip:
            geo_text = result.country
            if self.geo_coords:
                geo_text += f" ({result.latitude},{result.longitude})"
            row.append(geo_text)
        
        return row

    async def _scan_port(self, ip: str, port: int) -> Optional[ScanResult]:
        """Scan a single port"""
        # Check if port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        try:
            result = sock.connect_ex((ip, port))
            if result != 0:
                return None
        except Exception:
            return None
        finally:
            sock.close()
        
        # Try to ping Minecraft server
        ping_result = self._minecraft_ping(ip, port)
        if not ping_result:
            return None
        
        # Check version filter
        if not self._matches_version_filter(ping_result['version']):
            return None
        
        # Check player count filters
        if ping_result['players_online'] < self.min_players:
            return None
        
        if self.max_players and ping_result['players_max'] > self.max_players:
            return None
        
        # Get GeoIP info if requested
        country, latitude, longitude = "", 0.0, 0.0
        if self.geo_ip:
            country, latitude, longitude = self._get_geoip_info(ip)
        
        return ScanResult(
            ip=ip,
            port=port,
            version=ping_result['version'],
            players_online=ping_result['players_online'],
            players_max=ping_result['players_max'],
            description=ping_result['description'],
            country=country,
            latitude=latitude,
            longitude=longitude
        )

    async def _scan_worker(self, queue: asyncio.Queue, results: List[ScanResult]):
        """Worker coroutine for scanning"""
        while True:
            try:
                ip, port = await asyncio.wait_for(queue.get(), timeout=1.0)
                result = await self._scan_port(ip, port)
                if result:
                    results.append(result)
                queue.task_done()
            except asyncio.TimeoutError:
                break
            except Exception as e:
                print(f"Error in scan worker: {e}")
                queue.task_done()

    async def run_scan(self) -> List[ScanResult]:
        """Run the main scan"""
        print(f"Scanning ports {self.scan_ports} on {self.scan_hosts} with {self.concurrency} connections.")
        
        # Parse IPs and ports
        ips = self._parse_ip_range(self.scan_hosts)
        ports = self._parse_port_range(self.scan_ports)
        
        # Create scan queue
        queue = asyncio.Queue()
        results = []
        
        # Add all IP:port combinations to queue
        for ip in ips:
            for port in ports:
                await queue.put((ip, port))
        
        # Create workers
        workers = []
        for _ in range(min(self.concurrency, queue.qsize())):
            worker = asyncio.create_task(self._scan_worker(queue, results))
            workers.append(worker)
        
        # Wait for all tasks to complete
        await queue.join()
        
        # Cancel workers
        for worker in workers:
            worker.cancel()
        
        print("Scan finished!")
        return results

# =========================
# 🌐 Web Server
# =========================
app = Flask('MCSeeker Bot')

@app.route('/')
def home():
    return "MCSeeker Bot is running!"

def run_webserver():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server = Thread(target=run_webserver)
    server.daemon = True
    server.start()

# =========================
# 🤖 Discord Bot
# =========================
# Configure bot with necessary Intents
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Runs when the bot is connected and ready."""
    print(f'✅ Bot connected as {bot.user}')
    
    try:
        # Try to sync commands to a specific server if GUILD_ID is provided
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            synced = await bot.tree.sync(guild=guild)
            print(f'✅ Commands synced to guild {GUILD_ID}: {len(synced)}')
        else:
            # Per-guild sync for immediate availability in all servers
            total = 0
            for g in bot.guilds:
                try:
                    synced = await bot.tree.sync(guild=g)
                    total += len(synced)
                    print(f"✅ Commands synced to guild {g.id}: {len(synced)}")
                except Exception as e:
                    print(f"❌ Error syncing to guild {getattr(g, 'id', '?')}: {e}")
            # Also sync globally in background
            try:
                global_synced = await bot.tree.sync()
                print(f'ℹ️ Global sync launched: {len(global_synced)} commands (may take time to propagate)')
            except Exception as e:
                print(f'⚠️ Could not do global sync: {e}')
    except Exception as e:
        print(f'❌ Error syncing commands: {e}')

# =========================
# 📤 Utility Functions
# =========================
def _chunk_text_by_lines(text: str, max_chars: int = 1800) -> list[str]:
    lines = text.splitlines()
    chunks = []
    current = ''
    for ln in lines:
        add = ln + "\n"
        if len(current) + len(add) > max_chars:
            if current:
                chunks.append(current.rstrip('\n'))
                current = ''
            # If a single line exceeds the limit, cut it into hard chunks
            while len(add) > max_chars:
                chunks.append(add[:max_chars])
                add = add[max_chars:]
        current += add
    if current:
        chunks.append(current.rstrip('\n'))
    return chunks

async def send_large_text(interaction: discord.Interaction, header: str, body: str):
    """Send everything at once: if it exceeds the limit, attach a single .txt file."""
    if not body:
        await interaction.edit_original_response(content=header)
        return
    full_text = f"{body}"
    if len(full_text) <= 1800:
        await interaction.edit_original_response(content=f"{header}\n```\n{full_text}\n```")
    else:
        data = io.BytesIO(full_text.encode('utf-8', errors='ignore'))
        file = File(fp=data, filename='scan-results.txt')
        try:
            await interaction.edit_original_response(content=f"{header}\n(file attached)", attachments=[file])
        except discord.errors.HTTPException:
            data.seek(0)
            await interaction.followup.send(content=f"{header}\n(file attached)", files=[file])

def build_timestamped_csv_path(base_name: str = 'scan') -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scans_dir = os.path.join(base_dir, 'scans')
    try:
        os.makedirs(scans_dir, exist_ok=True)
    except Exception:
        pass
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return os.path.join(scans_dir, f'{base_name}_{ts}.csv')

# =========================
# 🎯 Discord Commands
# =========================

@bot.tree.command(name='scan', description='Run Minecraft server scan with Python scanner (no Node.js required).')
@app_commands.describe(
    ip='IP or range (e.g., 1.2.3.4 or 1.2.3.0/24)',
    port='Port or port range (default: 25565-25566)',
    min_players='Filter by minimum number of players',
    max_players='Filter by maximum number of players',
    version='Filter by server version (e.g., 1.20.*)',
    conc='Define number of concurrent connections',
    show_desc='Show server MOTD description',
    geo_ip='Enable GeoIP location detection',
    geo_coords='Include coordinates in GeoIP',
    timeout='Maximum wait time per server (in seconds)',
    enable_client='Enable Minecraft client connection',
    client_token='Client authentication token',
    out='Save results to file (e.g., result.csv)',
    format='Output format (csv, txt, txt-connect-only)',
    quiet='Quiet mode: no console output',
    maxmind_key='MaxMind download key for GeoIP database',
    extra='Additional flags (e.g., --show-desc --format csv)'
)
@app_commands.rename(
    min_players='min_players', max_players='max_players', show_desc='show_desc',
    geo_ip='geo_ip', geo_coords='geo_coords', enable_client='enable_client',
    client_token='client_token', maxmind_key='maxmind_key'
)
async def scan_command(
    interaction: discord.Interaction,
    ip: str,  # Required
    port: str = '25565-25566',
    min_players: app_commands.Range[int, 0] = None,
    max_players: app_commands.Range[int, 0] = None,
    version: str = None,
    conc: app_commands.Range[int, 1] = None,
    show_desc: bool = False,
    geo_ip: bool = False,
    geo_coords: bool = False,
    timeout: app_commands.Range[int, 1] = None,
    enable_client: bool = False,
    client_token: str = None,
    out: str = None,
    format: str = None,
    quiet: bool = False,
    maxmind_key: str = None,
    extra: str = None
):
    # Immediate response to avoid token expiration
    await interaction.response.send_message(f'⏳ Running scan with Python scanner, this may take a while...', ephemeral=False)

    try:
        # Build scanner arguments
        scanner_args = {
            'ip': ip,
            'port': port,
            'min_players': min_players,
            'max_players': max_players,
            'version': version,
            'conc': conc,
            'timeout': timeout,
            'out': out,
            'format': format,
            'show_desc': show_desc,
            'geo_ip': geo_ip,
            'geo_coords': geo_coords,
            'enable_client': enable_client,
            'client_token': client_token,
            'quiet': quiet,
            'maxmind_key': maxmind_key
        }

        # Remove None values
        scanner_args = {k: v for k, v in scanner_args.items() if v is not None}

        # Create scanner and run
        scanner = MinecraftScanner(scanner_args)
        results = await scanner.run_scan()

        # Format results for Discord
        if not results:
            await interaction.edit_original_response(content='⚠️ No Minecraft servers found matching your criteria.')
            return

        # Format results
        result_lines = []
        for result in results:
            if scanner.output_format == 'csv':
                row = scanner._format_csv_row(result)
                result_lines.append(','.join(str(x) for x in row))
            else:
                result_lines.append(scanner._format_result_line(result))

        # Send results
        result_text = '\n'.join(result_lines)
        await send_large_text(interaction, f'✅ Scan completed! Found {len(results)} servers:', result_text)

        # Save to file if requested
        if out:
            try:
                with open(out, 'w', newline='', encoding='utf-8') as f:
                    if scanner.output_format == 'csv':
                        writer = csv.writer(f)
                        for result in results:
                            writer.writerow(scanner._format_csv_row(result))
                    else:
                        for result in results:
                            f.write(scanner._format_result_line(result) + '\n')
                
                # Send file to Discord
                with open(out, 'rb') as f:
                    file = File(f, filename=out)
                    await interaction.followup.send(content=f'📁 Results saved to {out}', files=[file], ephemeral=True)
            except Exception as e:
                await interaction.followup.send(content=f'❌ Error saving file: {e}', ephemeral=True)

    except Exception as e:
        error_message = f"❌ **Error during scan:** {type(e).__name__}: {str(e)}"
        if len(error_message) > 2000:
            error_message = error_message[:1950] + "..."
        await interaction.edit_original_response(content=error_message)

@bot.tree.command(name='fullscan', description='Complete scan with recommended options and timestamped CSV output.')
@app_commands.describe(
    ip='IP or range (default: 0.0.0.0/0 for everything)',
    port='(Optional) Port range; if omitted, uses 25565-25566',
    min_players='Filter by minimum number of players',
    max_players='Filter by maximum number of players',
    version='Filter by server version (e.g., 1.20.*)',
    conc='Define number of concurrent connections (default 512 for fullscan)',
    show_desc='Show server MOTD description',
    geo_ip='Enable GeoIP location detection',
    geo_coords='Include coordinates in GeoIP',
    timeout='Maximum wait time per server (in seconds)',
    enable_client='Enable internal client connection',
    client_token='Client token for connecting to servers',
    quiet='Quiet mode: no console output',
    maxmind_key='MaxMind key for GeoIP database download',
    extra='Additional flags (e.g., --show-desc --format csv)'
)
async def fullscan_command(
    interaction: discord.Interaction,
    ip: str = '0.0.0.0/0',
    port: str = None,
    min_players: app_commands.Range[int, 0] = None,
    max_players: app_commands.Range[int, 0] = None,
    version: str = None,
    conc: app_commands.Range[int, 1] = None,
    show_desc: bool = True,
    geo_ip: bool = False,
    geo_coords: bool = False,
    timeout: app_commands.Range[int, 1] = None,
    enable_client: bool = False,
    client_token: str = None,
    quiet: bool = False,
    maxmind_key: str = None,
    extra: str = None
):
    await interaction.response.send_message('⏳ Running FULLSCAN and showing everything at the end...', ephemeral=False)

    try:
        # Build args like /scan but with fullscan defaults
        scanner_args = {
            'ip': ip,
            'port': port,
            'min_players': min_players,
            'max_players': max_players,
            'version': version,
            'conc': conc if conc is not None else 512,  # Default 512 for fullscan
            'timeout': timeout if timeout is not None else 15,
            'show_desc': show_desc,
            'geo_ip': geo_ip,
            'geo_coords': geo_coords,
            'enable_client': enable_client,
            'client_token': client_token,
            'quiet': quiet,
            'maxmind_key': maxmind_key,
            'format': 'csv',
            'out': build_timestamped_csv_path('fullscan')
        }

        # Remove None values
        scanner_args = {k: v for k, v in scanner_args.items() if v is not None}

        # Create scanner and run
        scanner = MinecraftScanner(scanner_args)
        results = await scanner.run_scan()

        if not results:
            await interaction.edit_original_response(content='⚠️ No Minecraft servers found matching your criteria.')
            return

        # Build comprehensive results
        result_lines = []
        connect_only = []
        by_version = {}
        total_servers = len(results)
        total_online = 0
        total_max = 0

        for result in results:
            # CSV format
            row = scanner._format_csv_row(result)
            result_lines.append(','.join(str(x) for x in row))
            
            # Connect only
            connect_only.append(f"{result.ip}:{result.port}")
            
            # Version stats
            version = result.version
            by_version[version] = by_version.get(version, 0) + 1
            
            # Player stats
            total_online += result.players_online
            total_max += result.players_max

        # Build summary
        summary_lines = [f"Total servers: {total_servers}"]
        if total_max > 0:
            summary_lines.append(f"Players online (estimated): {total_online}/{total_max}")
        if by_version:
            summary_lines.append("By version:")
            for ver, count in sorted(by_version.items(), key=lambda x: (-x[1], x[0])):
                summary_lines.append(f"- {ver}: {count}")

        # Combine all results
        combined = []
        combined.append("=== Raw results (csv) ===")
        combined.extend(result_lines or ['(no data)'])
        combined.append("")
        combined.append("=== Connect only (ip:port) ===")
        combined.extend(connect_only or ['(no data)'])
        combined.append("")
        combined.append("=== Summary ===")
        combined.extend(summary_lines)

        await send_large_text(interaction, '✅ FULLSCAN results:', "\n".join(combined))

        # Send CSV file
        try:
            with open(scanner_args['out'], 'rb') as f:
                file = File(f, filename=os.path.basename(scanner_args['out']))
                await interaction.followup.send(content=f'📁 Full results saved to {scanner_args["out"]}', files=[file], ephemeral=True)
        except Exception as e:
            await interaction.followup.send(content=f'❌ Error saving file: {e}', ephemeral=True)

    except Exception as e:
        error_message = f"❌ **Error during fullscan:** {type(e).__name__}: {str(e)}"
        if len(error_message) > 2000:
            error_message = error_message[:1950] + "..."
        await interaction.edit_original_response(content=error_message)

@bot.tree.command(name='help', description='Show detailed help about commands and their functions.')
async def help_command(interaction: discord.Interaction):
    help_text = """
**📘 Available commands:**

**/scan**
> Run your Minecraft scanner directly from Discord using Python (no Node.js required).
> **Main options:**
> - `ip` → IP or range (**required**).
> - `port` → Port or port range (default: 25565-25566).
> - `min_players` / `max_players` → Filter by number of connected players.
> - `version` → Filter by Minecraft version (e.g., 1.20.*).
> - `conc` → Define how many concurrent connections to use (default: 256).
> - `show_desc` → Show server MOTD.
> - `geo_ip` → Enable IP geolocation (requires GeoLite2.mmdb database).
> - `geo_coords` → Include coordinates (latitude, longitude).
> - `enable_client` → Enable Minecraft client connection.
> - `client_token` → Token for client authentication.
> - `out` → Save results to file.
> - `format` → Change format (csv, txt, txt-connect-only).
> - `quiet` → No console output, only save file.
> - `maxmind_key` → MaxMind key to download GeoIP database.

**Example usage:**
`/scan ip:mc.hypixel.net port:25565 show_desc:true geo_ip:true`

**/fullscan**
> Run a complete scan with recommended options and save CSV with timestamp.

**/help**
> Show this detailed help.
"""
    await interaction.response.send_message(content=help_text, ephemeral=True)

# =========================
# 🚀 Main Execution
# =========================
def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description='MCSeeker Unified Bot - Discord Bot with Integrated Minecraft Scanner')
    
    # Bot mode vs CLI mode
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode instead of Discord bot mode')
    
    # Main scan options (for CLI mode)
    parser.add_argument('--ip', help='IP or range to scan (default: 0.0.0.0/0)')
    parser.add_argument('--port', help=f'Port or port range (default: {MINECRAFT_DEFAULT_PORT})')
    parser.add_argument('--min-players', type=int, help='Minimum players filter')
    parser.add_argument('--max-players', type=int, help='Maximum players filter')
    parser.add_argument('--version', help='Version filter (default: *)')
    parser.add_argument('--conc', type=int, help=f'Concurrency level (default: {DEFAULT_CONCURRENCY})')
    parser.add_argument('--timeout', type=int, help=f'Timeout in seconds (default: {DEFAULT_TIMEOUT})')
    
    # Output options
    parser.add_argument('--out', help='Output file')
    parser.add_argument('--format', choices=['csv', 'txt', 'txt-connect-only'], help='Output format')
    parser.add_argument('--show-desc', action='store_true', help='Show server description')
    parser.add_argument('--quiet', action='store_true', help='Quiet mode (no console output)')
    
    # GeoIP options
    parser.add_argument('--geo-ip', action='store_true', help='Enable GeoIP lookup')
    parser.add_argument('--geo-coords', action='store_true', help='Include coordinates in GeoIP')
    parser.add_argument('--maxmind-key', help='MaxMind download key for GeoIP database')
    
    # Client options
    parser.add_argument('--enable-client', action='store_true', help='Enable Minecraft client connection')
    parser.add_argument('--client-token', help='Client authentication token')
    
    args = parser.parse_args()
    
    # Check dependencies
    if not JAVA_SERVER_AVAILABLE:
        print("Warning: mcstatus library not available. Install with: pip install mcstatus")
        print("Falling back to manual implementation.")
    
    if args.geo_ip and not MAXMIND_AVAILABLE:
        print("Error: maxminddb library required for GeoIP. Install with: pip install maxminddb")
        sys.exit(1)
    
    if args.cli:
        # CLI mode
        try:
            # Convert argparse args to dict
            scanner_args = {
                'ip': args.ip,
                'port': args.port,
                'min_players': args.min_players,
                'max_players': args.max_players,
                'version': args.version,
                'conc': args.conc,
                'timeout': args.timeout,
                'out': args.out,
                'format': args.format,
                'show_desc': args.show_desc,
                'geo_ip': args.geo_ip,
                'geo_coords': args.geo_coords,
                'enable_client': args.enable_client,
                'client_token': args.client_token,
                'quiet': args.quiet,
                'maxmind_key': args.maxmind_key
            }
            
            # Remove None values
            scanner_args = {k: v for k, v in scanner_args.items() if v is not None}
            
            # Create scanner and run
            scanner = MinecraftScanner(scanner_args)
            results = asyncio.run(scanner.run_scan())
            
            # Print results if not quiet
            if not args.quiet:
                for result in results:
                    print(scanner._format_result_line(result))
            
            # Save to file if requested
            if args.out:
                try:
                    with open(args.out, 'w', newline='', encoding='utf-8') as f:
                        if args.format == 'csv':
                            writer = csv.writer(f)
                            for result in results:
                                writer.writerow(scanner._format_csv_row(result))
                        else:
                            for result in results:
                                f.write(scanner._format_result_line(result) + '\n')
                    print(f"Results saved to {args.out}")
                except Exception as e:
                    print(f"Error saving file: {e}")
                    
        except KeyboardInterrupt:
            print("\nScan interrupted by user.")
        except Exception as e:
            print(f"Error during scan: {e}")
            sys.exit(1)
    else:
        # Discord bot mode
        if not TOKEN:
            print("❌ Error: DISCORD_TOKEN not found. Make sure you have a .env file or environment variable configured.")
            sys.exit(1)
        
        try:
            # Start web server to keep bot alive
            keep_alive()
            
            # Run the bot
            bot.run(TOKEN)
        except discord.LoginFailure as e:
            print(f'❌ Login error. Invalid token: {e}')
            sys.exit(1)
        except Exception as e:
            print(f'❌ Error starting bot: {e}')
            sys.exit(1)

if __name__ == '__main__':
    main()
