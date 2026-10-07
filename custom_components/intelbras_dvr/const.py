"""Constantes do componente intelbras_dvr."""
from __future__ import annotations

DOMAIN = "intelbras_dvr"
PLATFORMS = ["binary_sensor", "camera", "sensor"]

CONF_CHANNELS = "channels"
CONF_TRACK_BY_MAC = "track_by_mac"
CONF_RTSP_PORT = "rtsp_port"
CONF_RTSP_SUBTYPE = "rtsp_subtype"
CONF_HTTP_PORT = "http_port"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_EVENT_CODES = "event_codes"
CONF_EVENT_AUTO_OFF = "event_auto_off"

DEFAULT_USERNAME = "admin"
DEFAULT_CHANNELS = 4
DEFAULT_RTSP_PORT = 554
DEFAULT_RTSP_SUBTYPE = 0  # 0 = stream principal, 1 = substream
DEFAULT_HTTP_PORT = 80
DEFAULT_SCAN_INTERVAL = 300  # segundos
DEFAULT_EVENT_CODES = ["VideoMotion"]
DEFAULT_EVENT_AUTO_OFF = 60  # segundos; 0 desliga a rede de segurança

# CGI paths (compatível Intelbras/Dahua)
SNAPSHOT_CGI = "/cgi-bin/snapshot.cgi?channel={channel}"
MEDIAFILEFIND_CGI = "/cgi-bin/mediaFileFind.cgi"
RTSP_PATH = "/cam/realmonitor?channel={channel}&subtype={subtype}"
EVENTMANAGER_CGI = "/cgi-bin/eventManager.cgi?action=attach&codes=[{codes}]"
RTSP_PLAYBACK_PATH = "/cam/playback?channel={channel}&starttime={start}&endtime={end}"

# Media browser de gravações
MEDIA_BROWSE_DAYS = 7  # dias listados por canal
MEDIA_SLICE_MINUTES = 5  # granularidade dos trechos dentro de uma hora
HLS_MIME = "application/x-mpegURL"

# Estado armazenado em hass.data[DOMAIN][entry_id]
DATA_COORDINATOR = "coordinator"
DATA_LAST_RESULT = "last_result"
DATA_MAC = "mac"
DATA_LISTENER = "listener"

# Backoff por bloqueio (após 401)
LOGIN_LOCKOUT_BACKOFF = 300  # 5 min

# Códigos de evento suportados pelo eventManager (attach)
# SmartMotionHuman / SmartMotionVehicle são o SMD (Smart Motion Detection) do
# aparelho: o DVR levanta VideoMotion para QUALQUER mudança de pixel e, alguns
# segundos depois, emite um destes dois se o classificador reconhecer pessoa
# ou veículo. Medido num MHDX 3116-C (firmware 4.001.00IB000.0.T):
#
#   13:55:47  VideoMotion       Start  canal 2
#   13:55:52  SmartMotionHuman  Start  canal 2
#   13:56:06  SmartMotionHuman  Stop   canal 2
#
# A diferença de volume é a razão de isto existir: na mesma instalação os 4
# canais somaram ~9.500 VideoMotion em 48h. Quem automatiza em cima de
# VideoMotion processa quase só árvore balançando e sombra passando.
#
# Exige SMD ligado no aparelho. Confira em:
#   /cgi-bin/configManager.cgi?action=getConfig&name=SmartMotionDetect
#     table.SmartMotionDetect[N].Enable=true
#     table.SmartMotionDetect[N].ObjectTypes.Human=true
# Canal com SMD desligado nunca emite o evento — sem erro e sem aviso, o
# sensor fica em 'off' para sempre.
EVENT_CODES = [
    "VideoMotion",
    "SmartMotionHuman",
    "SmartMotionVehicle",
    "CrossLineDetection",
    "CrossRegionDetection",
    "VideoLoss",
    "VideoBlind",
    "AlarmLocal",
]

# Sinal do dispatcher: f"{DOMAIN}_{entry_id}_event"
SIGNAL_EVENT = DOMAIN + "_{entry_id}_event"

# Backoff da reconexão do stream de eventos
EVENT_BACKOFF_MIN = 5
EVENT_BACKOFF_MAX = 300
