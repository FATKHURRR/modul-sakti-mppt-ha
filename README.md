# Modul Sakti MPPT — Home Assistant Integration

Monitor one or more **Modul Sakti MPPT** solar charge controllers in Home
Assistant over MQTT, with no manual YAML.

## Features

- Config flow only — no YAML.
- **Multi device**: add the integration again for each additional module;
  each entry only asks for a broker preset and the **Module ID**.
- Auto-creates sensors for battery/PV voltage, current, power, peak power,
  today/total energy, load %, temperatures, status code, WiFi RSSI, free
  heap, uptime, IP, and firmware version.
- Auto-creates binary sensors for load output / charging / battery full /
  warning / fault, plus every alarm and fault flag the module reports
  (created dynamically the first time each one is seen — no need to know
  them in advance).
- Subscribes to `mpptMon/<module_id>/TX`, matching the module's own web
  dashboard topic pattern.

## Installation (HACS)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo as
   type **Integration**.
2. Install "Modul Sakti MPPT", restart Home Assistant.
3. Settings → Devices & Services → Add Integration → search
   "Modul Sakti MPPT".
4. Pick the broker (Server 1 / Server 2) and enter the Module ID
   (e.g. `MPPT001`). Repeat step 3 for each additional module.

## Manual installation

Copy `custom_components/modul_sakti_mppt` into your Home Assistant
`config/custom_components/` folder and restart.
