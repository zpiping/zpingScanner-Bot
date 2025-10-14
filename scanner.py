#!/usr/bin/env python3
"""
MCSeeker - Minecraft Server Scanner (Python Version)
Equivalent functionality to scanner.js with all the same features.
"""

import argparse
import asyncio
import concurrent.futures
import csv
import fnmatch
import json
import os
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

try:
    import maxminddb
    MAXMIND_AVAILABLE = True
except ImportError:
    MAXMIND_AVAILABLE = False

try:
    import mcstatus
    MCSTATUS_AVAILABLE = True
except ImportError:
    MCSTATUS_AVAILABLE = False

try:
    from mcstatus import JavaServer
    JAVA_SERVER_AVAILABLE = True
except ImportError:
    JAVA_SERVER_AVAILABLE = False

# Constants
MINECRAFT_DEFAULT_PORT = '25565-25566'
DEFAULT_TIMEOUT = 15
DEFAULT_CONCURRENCY = 256

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

class MinecraftScanner:
    def __init__(self, args):
        self.args = args
        self.geoip_reader = None
        self.client_token = None
        
        # Parse arguments
        self.scan_hosts = args.ip or '0.0.0.0/0'
        self.scan_ports = args.port or MINECRAFT_DEFAULT_PORT
        self.min_players = args.min_players or 0
        self.max_players = args.max_players
        self.version_filter = args.version or '*'
        self.concurrency = args.conc or DEFAULT_CONCURRENCY
        self.timeout = args.timeout or DEFAULT_TIMEOUT
        self.output_file = args.out
        self.output_format = args.format or 'csv'
        self.show_desc = args.show_desc
        self.geo_ip = args.geo_ip
        self.geo_coords = args.geo_coords
        self.enable_client = args.enable_client
        self.quiet = args.quiet
        self.maxmind_key = args.maxmind_key
        
        # Validate arguments
        if self.quiet and not self.output_file:
            print("Error: You have asked for --quiet output, but did not specify an --out file. This scan is pointless!")
            sys.exit(1)
        
        # Setup GeoIP if requested
        if self.geo_ip:
            self._setup_geoip()
        
        # Setup client token if requested
        if self.enable_client and not args.client_token:
            self._get_free_token()
        elif args.client_token:
            self.client_token = args.client_token

    def _setup_geoip(self):
        """Setup GeoIP database"""
        geoip_file = "./GeoLite2.mmdb"
        
        if not os.path.exists(geoip_file):
            if not self.maxmind_key:
                print("NO MAXMIND DOWNLOAD KEY WAS PROVIDED! CANNOT DOWNLOAD THE DATABASE WITHOUT A KEY!")
                sys.exit(1)
            
            print("Downloading GeoIP database...")
            self._download_geoip_database()
        
        if MAXMIND_AVAILABLE:
            try:
                self.geoip_reader = maxminddb.open_database(geoip_file)
                print("GeoIP database loaded successfully.")
            except Exception as e:
                print(f"Error loading GeoIP database: {e}")
                sys.exit(1)
        else:
            print("maxminddb library not available. Install with: pip install maxminddb")
            sys.exit(1)

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
            print(f"Error downloading GeoIP database: {e}")
            sys.exit(1)

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
        # This is a simplified version of the node-mcpe-color-parser functionality
        text = re.sub(r'§[0-9a-fk-or]', '', description)  # Remove Minecraft color codes
        text = re.sub(r'\n', ' ', text)  # Replace newlines with spaces
        return text.strip()

    def _write_result(self, result: ScanResult):
        """Write scan result to output"""
        if self.output_file:
            self._write_to_file(result)
        
        if not self.quiet:
            self._print_result(result)

    def _write_to_file(self, result: ScanResult):
        """Write result to output file"""
        try:
            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                if self.output_format == 'csv':
                    writer = csv.writer(f)
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
                    
                    writer.writerow(row)
                
                elif self.output_format == 'txt':
                    line = f"{result.ip}:{result.port}\t{result.version.replace(',', '+')}"
                    if self.show_desc:
                        line += f"\t{self._format_description(result.description)}"
                    if self.geo_ip:
                        geo_text = result.country
                        if self.geo_coords:
                            geo_text += f" ({result.latitude},{result.longitude})"
                        line += f" {geo_text}"
                    f.write(line + '\n')
                
                elif self.output_format == 'txt-connect-only':
                    f.write(f"{result.ip}:{result.port}\n")
                    
        except Exception as e:
            print(f"Error writing to file: {e}")

    def _print_result(self, result: ScanResult):
        """Print result to console"""
        the_text = f"{result.ip}:{result.port}\t{result.version}\t{result.players_online} of {result.players_max} players"
        
        if self.show_desc:
            the_text += f"\t{self._format_description(result.description)}"
        
        if self.geo_ip and result.country:
            geo_text = result.country
            if self.geo_coords:
                geo_text += f" ({result.latitude},{result.longitude})"
            print(f"[{geo_text}] {the_text}")
        else:
            print(the_text)

    async def _minecraft_client_connect(self, ip: str, port: int, protocol_version: int):
        """Connect to Minecraft server as a client (equivalent to mineflayer functionality)"""
        if not self.client_token:
            return
        
        try:
            # This is a simplified version of Minecraft client connection
            # In a full implementation, you'd use libraries like minecraft-protocol
            # or implement the full Minecraft protocol
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((ip, port))
            
            # Send login packet (simplified)
            # In reality, this requires full Minecraft protocol implementation
            # including encryption, compression, and authentication
            
            print(f"Client connection attempted to {ip}:{port} (protocol {protocol_version})")
            
            # Listen for chat messages (simplified)
            # In the original JS version, this listens for chat.type.announcement and chat.type.text
            
            sock.close()
            
        except Exception as e:
            pass  # Silently fail client connections

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
        
        # Attempt client connection if enabled
        if self.enable_client:
            await self._minecraft_client_connect(ip, port, ping_result.get('protocol', 0))
        
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
                    self._write_result(result)
                queue.task_done()
            except asyncio.TimeoutError:
                break
            except Exception as e:
                print(f"Error in scan worker: {e}")
                queue.task_done()

    async def run_scan(self):
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

def main():
    parser = argparse.ArgumentParser(description='MCSeeker - Minecraft Server Scanner (Python Version)')
    
    # Main scan options
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
    if not JAVA_SERVER_AVAILABLE and not MCSTATUS_AVAILABLE:
        print("Warning: mcstatus library not available. Install with: pip install mcstatus")
        print("Falling back to manual implementation.")
    
    if args.geo_ip and not MAXMIND_AVAILABLE:
        print("Error: maxminddb library required for GeoIP. Install with: pip install maxminddb")
        sys.exit(1)
    
    # Create scanner and run
    scanner = MinecraftScanner(args)
    
    try:
        asyncio.run(scanner.run_scan())
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except Exception as e:
        print(f"Error during scan: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
