# MCSeeker Python Version

This is a Python equivalent of the original `scanner.js` with identical functionality.

## Features

- **Port Scanning**: Scan for open Minecraft servers on specified IP ranges and ports
- **Minecraft Server Detection**: Automatically detect and ping Minecraft servers
- **Version Filtering**: Filter servers by Minecraft version using wildcards
- **Player Count Filtering**: Filter by minimum/maximum player counts
- **GeoIP Support**: Get geographical location information for servers
- **Multiple Output Formats**: CSV, TXT, and connect-only formats
- **Client Connection**: Optional Minecraft client connection (simplified)
- **Concurrent Scanning**: Configurable concurrency for faster scanning
- **TheAltening Integration**: Automatic free token generation for client connections

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. For GeoIP support, you'll need a MaxMind license key to download the database.

## Usage

### Basic Usage

```bash
# Scan a single IP
python scanner.py --ip 192.168.1.1

# Scan a port range
python scanner.py --ip 192.168.1.1 --port 25565-25566

# Scan with minimum players filter
python scanner.py --ip 192.168.1.0/24 --min-players 5

# Save results to CSV
python scanner.py --ip 192.168.1.0/24 --out results.csv --format csv
```

### Advanced Usage

```bash
# Full scan with GeoIP and description
python scanner.py \
  --ip 0.0.0.0/0 \
  --port 25565-25566 \
  --min-players 1 \
  --version "1.20.*" \
  --show-desc \
  --geo-ip \
  --geo-coords \
  --maxmind-key YOUR_MAXMIND_KEY \
  --out scan_results.csv \
  --format csv \
  --conc 512

# Quiet mode (output only to file)
python scanner.py --ip 192.168.1.0/24 --quiet --out results.csv

# Enable client connections
python scanner.py --ip 192.168.1.1 --enable-client --client-token YOUR_TOKEN
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--ip` | IP or IP range to scan | `0.0.0.0/0` |
| `--port` | Port or port range | `25565-25566` |
| `--min-players` | Minimum players filter | `0` |
| `--max-players` | Maximum players filter | No limit |
| `--version` | Version filter (supports wildcards) | `*` |
| `--conc` | Concurrency level | `256` |
| `--timeout` | Timeout in seconds | `15` |
| `--out` | Output file path | None (console only) |
| `--format` | Output format (`csv`, `txt`, `txt-connect-only`) | `csv` |
| `--show-desc` | Show server description/MOTD | `False` |
| `--quiet` | Quiet mode (no console output) | `False` |
| `--geo-ip` | Enable GeoIP lookup | `False` |
| `--geo-coords` | Include coordinates in GeoIP | `False` |
| `--maxmind-key` | MaxMind license key for GeoIP database | None |
| `--enable-client` | Enable Minecraft client connections | `False` |
| `--client-token` | Client authentication token | Auto-generated |

## Output Formats

### CSV Format
```csv
IP:PORT,VERSION,PLAYERS_ONLINE/PLAYERS_MAX,DESCRIPTION,COUNTRY
192.168.1.1:25565,1.20.1,5/20,My Server,US
```

### TXT Format
```
192.168.1.1:25565	1.20.1	5 of 20 players	My Server US
```

### Connect-Only Format
```
192.168.1.1:25565
192.168.1.2:25565
```

## GeoIP Setup

To use GeoIP functionality:

1. Get a MaxMind license key from [MaxMind](https://www.maxmind.com/)
2. Run with `--geo-ip --maxmind-key YOUR_KEY`
3. The database will be automatically downloaded and cached

## Differences from JavaScript Version

- **Minecraft Client**: The client connection functionality is simplified due to the complexity of implementing the full Minecraft protocol in Python
- **Dependencies**: Uses Python libraries (`mcstatus`, `maxminddb`) instead of Node.js packages
- **Performance**: Generally similar performance, but may vary depending on system and library implementations

## Error Handling

The script handles various error conditions:
- Network timeouts
- Invalid IP ranges
- Missing dependencies
- File I/O errors
- GeoIP database issues

## Examples

### Find popular servers
```bash
python scanner.py --ip 192.168.1.0/24 --min-players 10 --show-desc
```

### Export server list for later use
```bash
python scanner.py --ip 10.0.0.0/8 --out servers.csv --format csv --quiet
```

### Find specific version servers
```bash
python scanner.py --ip 0.0.0.0/0 --version "1.20.*" --max-players 50
```

### Scan with geographical information
```bash
python scanner.py --ip 192.168.1.0/24 --geo-ip --geo-coords --maxmind-key YOUR_KEY
```

## Troubleshooting

1. **"mcstatus library not available"**: Install with `pip install mcstatus`
2. **"maxminddb library required for GeoIP"**: Install with `pip install maxminddb`
3. **"No token obtained from TheAltening API"**: The API may be temporarily unavailable
4. **Slow scanning**: Reduce concurrency with `--conc 128` or increase timeout with `--timeout 30`

## License

This Python version maintains the same functionality as the original JavaScript scanner.js.

