# zpingScanner Bot

Un bot de Discord completamente funcional que incluye un scanner de servidores Minecraft integrado en Python. **Requiere Node.js**.

## ✨ Características

### 🤖 Bot de Discord
- **Comandos slash** modernos de Discord
- **Integración completa** con Discord API
- **Webserver integrado** para mantener el bot activo
- **Manejo de errores** robusto
- **Respuestas fragmentadas** para textos largos

### 🔍 Scanner de Minecraft
- **Escaneo de puertos** concurrente con asyncio
- **Detección automática** de servidores Minecraft
- **Filtros avanzados** por versión y jugadores
- **Soporte GeoIP** con MaxMind
- **Múltiples formatos** de salida (CSV, TXT, Connect-only)
- **Conexión de cliente** opcional (simplificada)
- **Integración con TheAltening** para tokens gratuitos

### 🎯 Modos de Ejecución
1. **Modo Discord Bot** (por defecto)
2. **Modo CLI** para uso desde terminal

## 📦 Instalación

### 1. Clonar/Descargar
```bash
# Si tienes git
git clone https://github.com/zpiping/bot-host-test.git
cd MCSeeker

# O descargar y extraer los archivos
```

### 2. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno
Crear archivo `.env`:
```env
DISCORD_TOKEN=tu_token_de_discord_aqui
GUILD_ID=tu_guild_id_opcional
```

### 4. Obtener Token de Discord
1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Crea una nueva aplicación
3. Ve a "Bot" → "Token" → "Copy"
4. Pega el token en tu archivo `.env`

## 🚀 Uso

### Modo Discord Bot (Recomendado)

```bash
python unified_bot.py
```

**Comandos disponibles:**

#### `/scan` - Escaneo básico
```
/scan ip:192.168.1.1 port:25565 show_desc:true
/scan ip:0.0.0.0/0 min_players:5 version:"1.20.*"
```

#### `/fullscan` - Escaneo completo
```
/fullscan ip:192.168.1.0/24 geo_ip:true
/fullscan ip:0.0.0.0/0 min_players:10 version:"1.20.*" conc:512
```

#### `/help` - Ayuda detallada
```
/help
```

### Modo CLI (Terminal)

```bash
# Escaneo básico
python unified_bot.py --cli --ip 192.168.1.1 --port 25565

# Escaneo completo con GeoIP
python unified_bot.py --cli --ip 192.168.1.0/24 --geo-ip --maxmind-key TU_KEY --out results.csv

# Escaneo con filtros
python unified_bot.py --cli --ip 0.0.0.0/0 --min-players 5 --version "1.20.*" --show-desc
```

## 🔧 Opciones de Configuración

### Argumentos Principales
| Argumento | Descripción | Ejemplo |
|-----------|-------------|---------|
| `--ip` | IP o rango a escanear | `192.168.1.0/24` |
| `--port` | Puerto o rango | `25565-25566` |
| `--min-players` | Mínimo de jugadores | `5` |
| `--max-players` | Máximo de jugadores | `100` |
| `--version` | Filtro de versión | `1.20.*` |
| `--conc` | Concurrencia | `512` |
| `--timeout` | Timeout en segundos | `15` |

### Opciones de Salida
| Argumento | Descripción |
|-----------|-------------|
| `--out` | Archivo de salida |
| `--format` | Formato (csv, txt, txt-connect-only) |
| `--show-desc` | Mostrar descripción del servidor |
| `--quiet` | Modo silencioso |

### GeoIP
| Argumento | Descripción |
|-----------|-------------|
| `--geo-ip` | Habilitar GeoIP |
| `--geo-coords` | Incluir coordenadas |
| `--maxmind-key` | Clave de MaxMind |

### Cliente Minecraft
| Argumento | Descripción |
|-----------|-------------|
| `--enable-client` | Habilitar conexión de cliente |
| `--client-token` | Token de autenticación |

## 📊 Formatos de Salida

### CSV
```csv
IP:PORT,VERSION,PLAYERS,DESCRIPTION,COUNTRY
192.168.1.1:25565,1.20.1,5/20,My Server,US
```

### TXT
```
192.168.1.1:25565	1.20.1	5 of 20 players	My Server US
```

### Connect-Only
```
192.168.1.1:25565
192.168.1.2:25565
```

## 🌍 Configuración GeoIP

### 1. Obtener Clave de MaxMind
1. Regístrate en [MaxMind](https://www.maxmind.com/)
2. Crea una cuenta gratuita
3. Genera una licencia
4. Usa la clave en `--maxmind-key`

### 2. Usar GeoIP
```bash
# Modo CLI
python unified_bot.py --cli --ip 192.168.1.0/24 --geo-ip --maxmind-key TU_CLAVE

# Modo Discord
/fullscan ip:192.168.1.0/24 geo_ip:true maxmind_key:TU_CLAVE
```

## 🔐 Configuración de Discord

### 1. Permisos del Bot
En Discord Developer Portal, habilita:
- **Bot** (Token)
- **Applications Commands** (Comandos slash)
- **Send Messages**
- **Use Slash Commands**

### 2. Invitar el Bot
```
https://discord.com/api/oauth2/authorize?client_id=TU_CLIENT_ID&permissions=2048&scope=bot%20applications.commands
```

### 3. Sincronización de Comandos
- Los comandos se sincronizan automáticamente
- Puede tomar hasta 1 hora para propagarse globalmente
- Usa `GUILD_ID` en `.env` para sincronización inmediata en un servidor específico

## 🎮 Ejemplos de Uso

### Encontrar Servidores Populares
```bash
# Discord
/fullscan ip:0.0.0.0/0 min_players:10 version:"1.20.*" show_desc:true

# CLI
python unified_bot.py --cli --ip 0.0.0.0/0 --min-players 10 --version "1.20.*" --show-desc
```

### Escaneo de Red Local
```bash
# Discord
/scan ip:192.168.1.0/24 port:25565-25566 show_desc:true geo_ip:true

# CLI
python unified_bot.py --cli --ip 192.168.1.0/24 --port 25565-25566 --show-desc --geo-ip
```

### Exportar Lista de Servidores
```bash
# Discord
/scan ip:10.0.0.0/8 out:servers.csv format:csv quiet:true

# CLI
python unified_bot.py --cli --ip 10.0.0.0/8 --out servers.csv --format csv --quiet
```

### Buscar Servidores Específicos
```bash
# Discord
/scan ip:0.0.0.0/0 version:"1.20.*" max-players:50 min-players:1

# CLI
python unified_bot.py --cli --ip 0.0.0.0/0 --version "1.20.*" --max-players 50 --min-players 1
```

## 🚨 Solución de Problemas

### Errores Comunes

1. **"mcstatus library not available"**
   ```bash
   pip install mcstatus
   ```

2. **"maxminddb library required for GeoIP"**
   ```bash
   pip install maxminddb
   ```

3. **"DISCORD_TOKEN not found"**
   - Verifica que el archivo `.env` existe
   - Verifica que el token es correcto
   - Asegúrate de que no hay espacios extra

4. **"No token obtained from TheAltening API"**
   - La API puede estar temporalmente no disponible
   - Usa `--client-token` con un token manual

5. **Escaneo lento**
   - Reduce concurrencia: `--conc 128`
   - Aumenta timeout: `--timeout 30`
   - Verifica tu conexión a internet

### Logs y Debugging
```bash
# Ver logs detallados
python unified_bot.py --cli --ip 127.0.0.1 --timeout 30

# Verificar conectividad
python unified_bot.py --cli --ip mc.hypixel.net --port 25565
```

## 🔄 Diferencias con el Sistema Original

| Característica | Original (JS) | Unificado (Python) |
|----------------|---------------|-------------------|
| **Dependencias** | Node.js + npm | Solo Python + pip |
| **Bot Discord** | Ejecuta scanner.js | Scanner integrado |
| **Performance** | Buena | Similar/Mejor |
| **Mantenimiento** | 2 archivos | 1 archivo |
| **Instalación** | npm + pip | Solo pip |

## 📝 Notas Importantes

- **No requiere Node.js** - Todo está en Python
- **Webserver integrado** - Mantiene el bot activo automáticamente
- **Manejo de errores** - Más robusto que el sistema original
- **Formatos de salida** - Idénticos al sistema original
- **Compatibilidad** - Funciona en Windows, Linux, macOS

## 🤝 Contribuciones

Este script unificado combina la funcionalidad de:
- `scanner.js` (Scanner de Minecraft)
- `main.py` (Bot de Discord)
- `webserver.py` (Servidor web)

Todo en un solo archivo `unified_bot.py` para máxima simplicidad.

## 📄 Licencia

Mantiene la misma funcionalidad que el sistema original JavaScript.


