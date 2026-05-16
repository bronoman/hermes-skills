---
name: openhab
description: Control and monitor local openHAB smart home server — items, things, rules, health checks, device status, battery levels, gateway monitoring, and system diagnostics via REST API.
version: 2.0.0
author: Hermes
auditor: bronoman
license: MIT
metadata:
  hermes:
    tags: [openHAB, Smart Home, REST API, Home Automation, Monitoring, Health Check, Diagnostics]
    homepage: https://www.openhab.org/docs/
    required_environment_variables:
      - OPENHAB_BASE_URL
      - OPENHAB_USERNAME
      - OPENHAB_PASSWORD
    # Optional: nice descriptions for the setup prompt
    config:
      openhab_base_url:
        description: "Full base URL of your openHAB instance (e.g. http://192.168.1.50:8080)"
        required: true
      openhab_username:
        description: "openHAB REST API username"
      openhab_password:
        description: "openHAB REST API password"
prerequisites:
  commands: [curl, jq]

---

# openHAB — Smart Home Control & Monitoring

Control and monitor your local openHAB server: items, things, rules, health checks, device status, battery levels, gateway monitoring, and system diagnostics.

## Server Details

| Item | Value                                                 |
|----------|---------------------------------------------------|
| Host     | `[IP_ADDRESS]`                                    |
| Port     | `8080`                                            |
| Base URL | `http://[IP_ADDRESS]:8080/rest/`                  |
| Auth     | HTTP Basic Auth (token-based, no password needed) |
| API Docs | `http://[IP_ADDRESS]:8080/docs`                   |

## Authentication

Use HTTP Basic Auth with every request. Username is an API token; password is empty.
Note the colon at the end (empty password).

## Quick Reference — Key Endpoints

| Endpoint              | Method | Purpose                                            |
|-----------------------|--------|----------------------------------------------------|
| `/items`              | GET    | List all items (discovery starting point)          |
| `/items/{name}/state` | GET    | Read current state of an item                      |
| `/items/{name}`       | POST   | Send command to item (payload = command string)    |
| `/items/{name}/state` | PUT    | Direct state change (bypass rules/logic)           |
| `/things`             | GET    | List all things/devices with metadata              |
| `/things/{uid}`       | GET    | Get specific thing details                         |
| `/rules`              | GET    | List all automation rules                          |
| `/rules/{uid}/runnow` | POST   | Trigger a rule manually                            |
| `/semantic/items`     | GET    | Query semantic model (rooms, equipment, hierarchy) |
| `/inbox`              | GET    | Discovery inbox (pending things)                   |
| `/config/services`    | GET    | System services status                             |
| `/systeminfo`         | GET    | Version, uptime, etc.                              |

## Common Operations

### List All Items (Discovery)

```bash
curl -s -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/items" | jq '.'
```

### Read Item State

```bash
curl -s -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/items/LivingRoom_Light/state"
```

### Send Command to Item

```bash
curl -s -X POST -u "${OPENHAB_USERNAME}:" \
  -H "Content-Type: text/plain" \
  -d "ON" \
  "${OPENHAB_BASE_URL}/rest/items/LivingRoom_Light"
```

**Command types:**
- **Switch**: `ON`, `OFF`
- **Dimmer**: `0` to `100` (percentage)
- **Number**: any numeric value
- **Color**: hex color code (e.g. `#FF0000`)
- **Rollershutter**: `UP`, `DOWN`, `0` to `100` (percentage open)

### Toggle a Light

```bash
LIGHT="LivingRoom_Light"
STATE=$(curl -s -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/items/${LIGHT}/state")
NEW_STATE=$([[ "$STATE" == "ON" ]] && echo "OFF" || echo "ON")
curl -s -X POST -u "${OPENHAB_USERNAME}:" \
  -H "Content-Type: text/plain" \
  -d "$NEW_STATE" \
  "${OPENHAB_BASE_URL}/rest/items/${LIGHT}"
echo "Toggled ${LIGHT} to $NEW_STATE"
```

### Direct State Change (Bypass Rules)

```bash
curl -s -X PUT -u "${OPENHAB_USERNAME}:" \
  -H "Content-Type: text/plain" \
  -d "OFF" \
  "${OPENHAB_BASE_URL}/rest/items/LivingRoom_Light/state"
```

**Difference:** `POST /items/{name}` (command) triggers rules and automations. `PUT /items/{name}/state` directly sets value without logic.

### List All Things (Devices)

```bash
curl -s -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/things" | jq '.[] | {uid, label, status}'
```

### Query Semantic Model (Rooms & Equipment)

```bash
curl -s -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/semantic/items" | jq '.items | group_by(.location)' 2>/dev/null || echo "Semantic model not available — install the semantics addon"
```

### List All Rules

```bash
curl -s -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/rules" | jq '.[] | {uid, name, enabled}'
```

### Trigger a Rule

```bash
curl -s -X POST -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/rules/RULE_UID/runnow"
```

### Search Items by Pattern (e.g. Light)

```bash
curl -s -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/items?recursive=false" | \
  jq '.[] | select(.name | contains("Light"))'
```

### Filter Items by Type (e.g. Switch)

```bash
curl -s -u "${OPENHAB_USERNAME}:" "${OPENHAB_BASE_URL}/rest/items" | \
  jq '.[] | select(.type=="Switch")'
```

## Query Parameters

Useful URL parameters for `/rest/items`:

- `recursive=true|false` — Include nested group items
- `fields=name,state,type,label` — Select specific fields only
- `tags=tag1,tag2` — Filter by tags
- `type=Switch,Dimmer` — Filter by item type

## Health Check — Full System Report (Python)

Run `python3 ~/.hermes/skills/smart-home/openhab/scripts/healthcheck.py` for a comprehensive report including items, things, rules, batteries, gateways, and Fibaro shutters.

## Rules Health Check Logic

| Rule Status     | Detail     | Meaning                                    |
|-----------------|------------|--------------------------------------------|
| `IDLE`          | —          | ✅ Healthy — waiting for triggers          |
| `UNINITIALIZED` | `DISABLED` | ✅ Intentionally turned off                |
| `INITIALIZING`  | —          | ⚠️ Starting up (should transition quickly) |
| `RUNNING`       | —          | ⚠️ Currently executing (prolonged = issue) |
| `FAILED`        | —          | ❌ Requires intervention                   |
| `WARNING`       | —          | ⚠️ Check recommended                       |
| `ERROR`         | —          | ❌ Requires intervention                   |

## Error Handling

| HTTP| Meaning                              |
|-----|--------------------------------------|
| 200 | Success                              |
| 201 | Created                              |
| 400 | Bad request (invalid command/format) |
| 401 | Unauthorized (bad credentials)       |
| 404 | Item/rule not found                  |
| 500 | Server error                         |

## Troubleshooting

| Symptom           | Cause | Solution |
|-------------------|-------------------------------|----------------------------------------|
| Server offline    | Network issue or service down | Check network, restart openHAB         |
| Auth failed (401) | Invalid credentials           | Verify API token in env vars           |
| Things OFFLINE    | Device connectivity lost      | Check power, WiFi, Zigbee/Z-Wave range |
| Items NULL state  | Binding error                 | Check binding logs, rediscover things  |
| High latency      | Server overload               | Monitor CPU/memory, optimize load      |

## Pitfalls

- **Auth required on every call** — Always use Basic Auth
- **Content-Type headers matter** — Commands expect `text/plain`, not JSON
- **Case sensitivity** — Item names are case-sensitive
- **Thing UIDs are URL-encoded** — Colons become `%3A`, spaces become `%20`
- **Rules can't be created via REST** — Only queried, enabled, disabled, or run
- **State changes don't trigger linked items** — Use command for full automation integration
- **PUT vs POST** — PUT to `/state` may return 415 on some configs; use POST to `/items/{name}` for commands
- **`.env` placeholder values** — If `OPENHAB_PASSWORD=***` is set as a literal placeholder in `.env`, the script sends `***` as the password. Always set to empty string (`OPENHAB_PASSWORD=`) for token-based auth.
- **Script permissions** — Health check script must be executable (`chmod 755 scripts/healthcheck.py`). Permissions 664 will cause "Permission denied" errors.
- **Semantic model** — The `/rest/semantic/items` endpoint requires the semantics addon. If it returns empty or 404, the addon isn't installed.

## Integration with Hermes

Use in cron jobs if user desires regular monitoring. Respond to natural language commands like:
- "turn on the living room light" → POST command to the light item
- "is the light in the entrance still on?" → GET state of the light item
- "what's the temperature in the bedroom?" → GET state of temperature item
- "check openHAB health" → run the full health check
- "are all my devices online?" → check things status
- "show me all lights" → filter items by type=Switch

## Support Files

- `references/openhab-api-examples.md` — REST API examples for device control and querying
- `scripts/healthcheck.py` — Full system health report (items, things, rules, batteries, gateways, shutters)
