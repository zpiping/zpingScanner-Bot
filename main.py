import os
import discord
from discord import app_commands, File
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import shlex # Para manejar la división segura de argumentos de cadena
import webserver
import shutil
import platform
import io
import re
from datetime import datetime
import zipfile

# Cargar variables de entorno del archivo .env
load_dotenv()

# =========================
# ⚙️ Configuración
# =========================
# Reemplaza con tus valores reales si no usas .env
TOKEN = os.getenv('DISCORD_TOKEN') 
GUILD_ID = os.getenv('GUILD_ID') # Opcional: el ID del servidor (guild) para comandos instantáneos

# Configurar el bot con los Intents necesarios
intents = discord.Intents.default()
intents.guilds = True # Necesario para comandos de aplicación
bot = commands.Bot(command_prefix='!', intents=intents)

# =========================
# 🔄 Sincronización de Comandos
# =========================
@bot.event
async def on_ready():
    """Se ejecuta cuando el bot está conectado y listo."""
    print(f'✅ Bot conectado como {bot.user}')

    try:
        # Intentar sincronizar comandos a un servidor específico si se proporciona GUILD_ID
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            # Sincroniza solo los comandos de este servidor para que aparezcan inmediatamente
            synced = await bot.tree.sync(guild=guild) 
            print(f'✅ Comandos sincronizados en guild {GUILD_ID}: {len(synced)}')
        else:
            # Sincronización por-guild para disponibilidad inmediata en todos los servidores
            total = 0
            for g in bot.guilds:
                try:
                    synced = await bot.tree.sync(guild=g)
                    total += len(synced)
                    print(f"✅ Comandos sincronizados en guild {g.id}: {len(synced)}")
                except Exception as e:
                    print(f"❌ Error al sincronizar en guild {getattr(g, 'id', '?')}: {e}")
            # También sincronizamos globalmente en background (no bloquea, solo info)
            try:
                global_synced = await bot.tree.sync()
                print(f'ℹ️ Sincronización global lanzada: {len(global_synced)} comandos (puede tardar en propagarse)')
            except Exception as e:
                print(f'⚠️ No se pudo hacer sync global: {e}')
    except Exception as e:
        print(f'❌ Error al sincronizar comandos: {e}')

# =========================
# 🔧 Helper para crear flags (argumentos de scanner.js)
# =========================
def build_scanner_args(interaction: discord.Interaction) -> list[str]:
    """
    Construye la lista de argumentos para el subproceso 'node scanner.js'
    a partir de las opciones de la interacción de barra diagonal.
    """
    args = ['scanner.js'] # NOTA: Esto se reemplazará por la ruta absoluta más abajo

    # Las opciones de slash command se pasan como argumentos de la función
    # Los obtenemos del diccionario de `Interaction.namespace`
    options = interaction.namespace

    # Argumentos obligatorios o de cadena/entero simple
    if options.ip:
        args.extend(['--ip', str(options.ip)])
    if options.port:
        args.extend(['--port', str(options.port)])
    if options.min_players is not None:
        args.extend(['--min-players', str(options.min_players)])
    if options.max_players is not None:
        args.extend(['--max-players', str(options.max_players)])
    if options.version:
        args.extend(['--version', str(options.version)])
    if options.conc is not None:
        args.extend(['--conc', str(options.conc)])
    if options.timeout is not None:
        args.extend(['--timeout', str(options.timeout)])
    if options.client_token:
        args.extend(['--client-token', str(options.client_token)])
    if options.out:
        args.extend(['--out', str(options.out)])
    if options.format:
        args.extend(['--format', str(options.format)])
    if options.maxmind_key:
        args.extend(['--maxmind-key', str(options.maxmind_key)])

    # Argumentos booleanos
    if options.show_desc:
        args.append('--show-desc')
    if options.geo_ip:
        args.append('--geo-ip')
    if options.geo_coords:
        args.append('--geo-coords')
    if options.enable_client:
        args.append('--enable-client')
    if options.quiet:
        args.append('--quiet')

    # Argumentos extra. Usamos shlex.split para dividir de forma segura
    if options.extra:
        try:
            extra_args = shlex.split(options.extra)
            args.extend(extra_args)
        except ValueError as e:
            # Manejo de error si la cadena extra no se puede dividir correctamente
            print(f"Error al procesar --extra: {e}")
            pass # Continúa sin los argumentos extra si fallan

    return args

# =========================
# 🔍 Resolución de Node.js / Validaciones previas
# =========================
def find_node_executable() -> str | None:
    """Intenta ubicar el ejecutable de Node.js de forma robusta, especialmente en Windows."""
    # 1) Buscar en PATH
    node_path = shutil.which('node')
    if node_path and os.path.exists(node_path):
        return node_path

    # 2) Rutas comunes en Windows
    if platform.system().lower().startswith('win'):
        candidates = []
        program_files = os.environ.get('ProgramFiles')
        program_files_x86 = os.environ.get('ProgramFiles(x86)')
        local_appdata = os.environ.get('LOCALAPPDATA')
        userprofile = os.environ.get('USERPROFILE')
        nvm_symlink = os.environ.get('NVM_SYMLINK')

        if program_files:
            candidates.append(os.path.join(program_files, 'nodejs', 'node.exe'))
        if program_files_x86:
            candidates.append(os.path.join(program_files_x86, 'nodejs', 'node.exe'))
        if local_appdata:
            candidates.append(os.path.join(local_appdata, 'Programs', 'nodejs', 'node.exe'))
        if nvm_symlink:
            candidates.append(os.path.join(nvm_symlink, 'node.exe'))
        if userprofile:
            candidates.append(os.path.join(userprofile, 'scoop', 'shims', 'node.exe'))

        for path in candidates:
            if path and os.path.exists(path):
                return path

    # 3) No encontrado
    return None

async def run_scanner_process(interaction: discord.Interaction, args: list[str]):
    """Ejecuta el scanner con validaciones previas y manejo de salida/errores."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scanner_full_path = os.path.join(base_dir, 'scanner.js')
        if not os.path.exists(scanner_full_path):
            await interaction.edit_original_response(content='❌ Error Crítico (Ruta): `scanner.js` no existe en el directorio de la app.')
            return

        node_exec = find_node_executable()
        if not node_exec:
            await interaction.edit_original_response(content='❌ Error Crítico (Ruta): No se encontró `node`. Instala Node.js y asegúrate de que esté en PATH.')
            return

        # Asegurar que el primer argumento sea la ruta absoluta a scanner.js
        if args:
            args[0] = scanner_full_path

        node_args = ['--no-deprecation']

        process = await asyncio.create_subprocess_exec(
            node_exec, *node_args, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout_data, stderr_data = await process.communicate()
        code = process.returncode

        stdout = stdout_data.decode('utf-8', errors='ignore').strip()

        stderr_raw = stderr_data.decode('utf-8', errors='ignore').strip()
        filtered = []
        for line in stderr_raw.splitlines():
            if line.startswith('(node:'):
                continue
            if line.startswith('(Use `node') and '--trace-deprecation' in line:
                continue
            filtered.append(line)
        lines = filtered
        stderr = '\n'.join(lines).strip()

        if not stdout:
            await interaction.edit_original_response(content=f'⚠️ El escaneo terminó (código {code}) sin salida.')
        else:
            await send_large_text(interaction, '✅ Resultado del escaneo:', stdout)

        if stderr:
            err_bytes = stderr.encode('utf-8', errors='ignore')
            err_file = File(fp=io.BytesIO(err_bytes), filename='scanner-stderr.txt')
            await interaction.followup.send(content='🚨 **Salida de error (stderr) detectada:**', files=[err_file], ephemeral=True)

    except FileNotFoundError:
        await interaction.edit_original_response(content='❌ **Error Crítico (Ruta):** No se pudo ejecutar `node` o `scanner.js`. Verifica la instalación de Node.js y la ubicación de `scanner.js`.')
    except Exception as e:
        error_message = f"❌ **Error Interno o de Ejecución:** El escaneo falló después de iniciar. Detalle: `{type(e).__name__}: {e}`"
        if len(error_message) > 2000:
            error_message = error_message[:1950] + "..."
        await interaction.edit_original_response(content=error_message)

async def run_scanner_raw(args: list[str]) -> tuple[int, str, str]:
    """Ejecuta el scanner y devuelve (code, stdout_str, stderr_str) sin tocar Discord."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scanner_full_path = os.path.join(base_dir, 'scanner.js')
    if not os.path.exists(scanner_full_path):
        return (127, '', 'scanner.js no existe en el directorio de la app')

    node_exec = find_node_executable()
    if not node_exec:
        return (127, '', 'No se encontró node en PATH ni rutas comunes')

    if args:
        args[0] = scanner_full_path

    node_args = ['--no-deprecation']

    process = await asyncio.create_subprocess_exec(
        node_exec, *node_args, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout_data, stderr_data = await process.communicate()
    code = process.returncode

    stdout = stdout_data.decode('utf-8', errors='ignore').strip()
    stderr_raw = stderr_data.decode('utf-8', errors='ignore').strip()

    filtered = []
    for line in stderr_raw.splitlines():
        if line.startswith('(node:'):
            continue
        if line.startswith('(Use `node') and '--trace-deprecation' in line:
            continue
        filtered.append(line)
    stderr = '\n'.join(filtered).strip()
    return (code, stdout, stderr)

# =========================
# 🧪 /fullscan Comando
# =========================
@bot.tree.command(name='fullscan', description='Escaneo completo y resultados directos en el chat (mismas opciones que /scan).')
@app_commands.describe(
    ip='IP o rango (ej: 0.0.0.0/0 para todo)',
    port='(Opcional) Rango de puertos; si omites, usa 25565-25566',
    min_players='Filtra por cantidad mínima de jugadores',
    max_players='Filtra por cantidad máxima de jugadores',
    version='Filtra por versión del servidor (ej: 1.20.*)',
    conc='Define el número de conexiones simultáneas (por defecto 512 en fullscan)',
    show_desc='Muestra el texto MOTD del servidor',
    geo_ip='Activa la detección GeoIP',
    geo_coords='Agrega coordenadas GeoIP al resultado',
    timeout='Tiempo máximo de espera por servidor (en segundos)',
    enable_client='Activa conexión del cliente interno (Mineflayer)',
    client_token='Token del cliente para conectarse a servidores',
    quiet='Modo silencioso: no muestra resultados en consola',
    maxmind_key='Clave de descarga de base de datos GeoIP',
    extra='Flags adicionales (ej: --show-desc --format csv)'
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
    extra: str = None,
    payloads: str = None
):
    await interaction.response.send_message('⏳ Ejecutando FULLSCAN y mostrando TODO al final...', ephemeral=False)

    # Construir args como /scan pero con defaults de fullscan
    args = ['scanner.js', '--ip', str(ip)]
    if port:
        args.extend(['--port', str(port)])
    if min_players is not None:
        args.extend(['--min-players', str(min_players)])
    if max_players is not None:
        args.extend(['--max-players', str(max_players)])
    if version:
        args.extend(['--version', str(version)])
    # conc por defecto 512 si no se indicó
    args.extend(['--conc', str(conc if conc is not None else 512)])
    # timeout por defecto 15 si no se indicó
    args.extend(['--timeout', str(timeout if timeout is not None else 15)])
    if show_desc:
        args.append('--show-desc')
    if geo_ip:
        args.append('--geo-ip')
    if geo_coords:
        args.append('--geo-coords')
    if enable_client:
        args.append('--enable-client')
    if client_token:
        args.extend(['--client-token', str(client_token)])
    if quiet:
        args.append('--quiet')
    if maxmind_key:
        args.extend(['--maxmind-key', str(maxmind_key)])
    if extra:
        try:
            args.extend(shlex.split(extra))
        except ValueError:
            pass
    if payloads:
        try:
            args.extend(shlex.split(payloads))
        except ValueError:
            pass

    code, raw_out, raw_err = await run_scanner_raw(args)

    # Derivar vistas a partir del stdout del escáner
    result_lines = []
    lines = [ln for ln in (raw_out or '').splitlines() if ln.strip()]
    result_re = re.compile(r'^(?:\[[^\]]+\]\s*)?\d{1,3}(?:\.\d{1,3}){3}:\d+\t')
    lines = [ln for ln in lines if result_re.match(ln)]
    # Convertir a pseudo-csv: ip:port,version,players
    for ln in lines:
        parts = ln.split('\t')
        if len(parts) >= 3:
            ipport = parts[0]
            ver = parts[1].replace(',', '+')
            players = parts[2]
            result_lines.append(f"{ipport},{ver},{players}")

    # Construir connect-only y resumen desde result_lines (csv-like)
    connect_only = []
    by_version = {}
    total_servers = 0
    total_online = 0
    total_max = 0

    for ln in result_lines:
        cols = [c.strip() for c in ln.split(',')]
        if len(cols) >= 3:
            ipport = cols[0]
            ver = cols[1]
            players = cols[2]
            connect_only.append(ipport)
            by_version[ver] = by_version.get(ver, 0) + 1
            try:
                nums = [int(x) for x in re.findall(r"\d+", players)]
                if len(nums) >= 2:
                    total_online += nums[0]
                    total_max += nums[1]
            except Exception:
                pass
            total_servers += 1

    summary_lines = [f"Total servidores: {total_servers}"]
    if total_max > 0:
        summary_lines.append(f"Jugadores online (estimado): {total_online}/{total_max}")
    if by_version:
        summary_lines.append("Por versión:")
        for ver, count in sorted(by_version.items(), key=lambda x: (-x[1], x[0])):
            summary_lines.append(f"- {ver}: {count}")

    combined = []
    combined.append("=== Resultados crudos (csv) ===")
    combined.extend(result_lines or ['(sin datos)'])
    combined.append("")
    combined.append("=== Connect only (ip:puerto) ===")
    combined.extend(connect_only or ['(sin datos)'])
    combined.append("")
    combined.append("=== Resumen ===")
    combined.extend(summary_lines)

    await send_large_text(interaction, '✅ FULLSCAN resultados:', "\n".join(combined))

# =========================
# 🧰 Utilidad: ruta CSV con timestamp en carpeta scans
# =========================
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
# 💬 Utilidad: enviar texto largo fragmentado al chat
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
            # Si una sola línea excede el límite, cortarla en trozos duros
            while len(add) > max_chars:
                chunks.append(add[:max_chars])
                add = add[max_chars:]
        current += add
    if current:
        chunks.append(current.rstrip('\n'))
    return chunks

async def send_large_text(interaction: discord.Interaction, header: str, body: str):
    """Envía todo de una vez: si supera el límite, adjunta un .txt único."""
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
            await interaction.edit_original_response(content=f"{header}\n(archivo adjunto)", attachments=[file])
        except discord.errors.HTTPException:
            data.seek(0)
            await interaction.followup.send(content=f"{header}\n(archivo adjunto)", files=[file])

# =========================
# ⚡ /scan Comando
# =========================
@bot.tree.command(name='scan', description='Ejecuta scanner.js (sin modificarlo) con los parámetros que elijas.')
@app_commands.describe(
    ip='IP o rango (ej: 1.2.3.4 o 1.2.3.0/24)',
    port='Puerto o rango (por defecto 25565-25566)',
    min_players='Filtra por cantidad mínima de jugadores',
    max_players='Filtra por cantidad máxima de jugadores',
    version='Filtra por versión del servidor (ej: 1.20.*)',
    conc='Define el número de conexiones simultáneas',
    show_desc='Muestra el texto MOTD del servidor',
    geo_ip='Activa la detección GeoIP',
    geo_coords='Agrega coordenadas GeoIP al resultado',
    timeout='Tiempo máximo de espera por servidor (en segundos)',
    enable_client='Activa conexión del cliente interno (Mineflayer)',
    client_token='Token del cliente para conectarse a servidores',
    out='Guarda resultados en archivo (ej: result.csv)',
    format='Formato de salida (csv, txt, etc.)',
    quiet='Modo silencioso: no muestra resultados en consola',
    maxmind_key='Clave de descarga de base de datos GeoIP',
    extra='Flags adicionales (ej: --show-desc --format csv)'
)
@app_commands.rename(
    min_players='min_players', max_players='max_players', show_desc='show_desc',
    geo_ip='geo_ip', geo_coords='geo_coords', enable_client='enable_client',
    client_token='client_token', maxmind_key='maxmind_key'
)
async def scan_command(
    interaction: discord.Interaction,
    ip: str, # Requerido
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
    # Respuesta inmediata para evitar la expiración del token
    await interaction.response.send_message(f'⏳ Ejecutando escaneo con `scanner.js`, esto puede tardar...', ephemeral=False)

    # Construir los argumentos y delegar en el helper unificado
    args = build_scanner_args(interaction)
    await run_scanner_process(interaction, args)


# =========================
# 🆘 /help Comando
# =========================
@bot.tree.command(name='help', description='Muestra ayuda detallada sobre los comandos y sus funciones.')
async def help_command(interaction: discord.Interaction):
    help_text = f"""
**📘 Comandos disponibles:**

**/scan**
> Ejecuta tu escáner *scanner.js* directamente desde Discord.
> **Opciones principales:**
> - `ip` → IP o rango (**obligatorio**).
> - `port` → Puerto o rango de puertos (por defecto 25565-25566).
> - `min_players` / `max_players` → Filtran por cantidad de jugadores conectados.
> - `version` → Filtra por versión de Minecraft (ej: 1.20.*).
> - `conc` → Define cuántas conexiones simultáneas usar (por defecto 256).
> - `show_desc` → Muestra el MOTD del servidor.
> - `geo_ip` → Activa geolocalización por IP (requiere base GeoLite2.mmdb).
> - `geo_coords` → Incluye coordenadas (latitud, longitud).
> - `enable_client` → Activa el cliente Mineflayer para intentar conectarse.
> - `client_token` → Token para autenticación del cliente.
> - `out` → Guarda resultados en archivo.
> - `format` → Cambia el formato (csv, txt, etc.).
> - `quiet` → No muestra salida en consola, sólo guarda archivo.
> - `maxmind_key` → Clave de MaxMind para descargar base GeoIP.

**Ejemplo de uso:**
`/scan ip:mc.hypixel.net port:25565 show_desc:true geo_ip:true`

**/fullscan**
> Ejecuta un escaneo completo con opciones recomendadas y guarda CSV con timestamp.

**/help**
> Muestra esta ayuda detallada.
"""
    await interaction.response.send_message(content=help_text, ephemeral=True)

webserver.keep_alive()  # Iniciar el servidor web para mantener el bot activo
# =========================
# 🚀 Iniciar bot
# =========================
if __name__ == '__main__':
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN no encontrado. Asegúrate de tener un archivo .env o la variable de entorno configurada.")
    else:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure as e:
            print(f'❌ Error al iniciar sesión. Token inválido: {e}')