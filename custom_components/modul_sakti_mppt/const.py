"""Constants for the Modul Sakti MPPT integration."""

DOMAIN = "modul_sakti_mppt"

CONF_SERVER = "server"
CONF_MODULE_ID = "module_id"

SIGNAL_UPDATE = f"{DOMAIN}_update_{{entry_id}}"
SIGNAL_NEW_KEYS = f"{DOMAIN}_new_keys_{{entry_id}}"

# Preset MQTT brokers. Users only pick one of these, they never type
# host/port/credentials by hand.
SERVERS = {
    "server1": {
        "label": "Server 1",
        "host": "broker.emqx.io",
        "port": 1883,
        "username": "emqx",
        "password": "emqx",
    },
    "server2": {
        "label": "Server 2",
        "host": "public.cloud.shiftr.io",
        "port": 1883,
        "username": "public",
        "password": "public",
    },
}

# Topic pattern used by the Modul Sakti MPPT firmware.
TOPIC_DATA = "mpptMon/{module_id}/TX"
TOPIC_LOG = "{module_id}/TX/log"

MANUFACTURER = "Modul Sakti"
MODEL = "MPPT Monitor"
