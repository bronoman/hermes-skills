---
name: openhab-healthcheck
description: Monitor and check health of local openHAB server — connectivity, bridge status, device availability, system diagnostics, offline/disabled items, and error logs
version: 1.3.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [openHAB, Smart Home, Monitoring, Health Check, Diagnostics, Logging]
    homepage: https://www.openhab.org/docs/
prerequisites:
  env_vars: [OPENHAB_BASE_URL, OPENHAB_USERNAME, OPENHAB_PASSWORD]
---

# openHAB Healthcheck Skill

Monitor the health and status of your local openHAB server, bridge connections, device availability, and system diagnostics.

## Quick Health Check

Verifies server connectivity, and basic system status:

```bash
#!/bin/bash
BASE_URL="${OPENHAB_BASE_URL:-http://192.168.1.10:8080}"
USER="${OPENHAB_USERNAME:-oh.Hermes.m3aG9XZppfjiYo4noYlRVISNE6TWPiW0uIOnoxG9fzOiLzYHYJ7fgfQGoOF2OwQphQySY8WOy99oddonBaq52A}"

echo "🔍 openHAB Health Check"
echo "======================"

# 1. Server ping test
echo -n "Server connectivity: "
if curl -s --connect-timeout 3 -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q 200; then
    echo "✅ ONLINE"
else
    echo "❌ OFFLINE"
    exit 1
fi

# 2. API authentication
echo -n "API authentication: "
HTTP_CODE=$(curl -s -u "$USER:" -o /dev/null -w "%{http_code}" "$BASE_URL/rest/items")
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ OK"
else
    echo "❌ FAILED ($HTTP_CODE)"
fi

# 3. Item count
ITEM_COUNT=$(curl -s -u "$USER:" "$BASE_URL/rest/items" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "Items: $ITEM_COUNT"

# 4. Things status summary
THINGS_DATA=$(curl -s -u "$USER:" "$BASE_URL/rest/things" | python3 -c "
import sys, json, collections
things = json.load(sys.stdin)
statuses = collections.Counter(t.get('statusInfo', {}).get('status', 'UNKNOWN') for t in things)
for status, count in sorted(statuses.items()):
    print(f'{status}:{count}')
")
echo "Things: $THINGS_DATA"

echo "✅ Health check complete"
```

## Detailed Health Checks (Python)

### 1. Full System Health Status

```python
#!/usr/bin/env python3
import json
import urllib.request
import base64
import sys
import os

BASE_URL = os.environ.get("OPENHAB_BASE_URL", "http://192.168.1.10:8080")
USERNAME = os.environ.get("OPENHAB_USERNAME", "oh.Hermes.m3aG9XZppfjiYo4noYlRVISNE6TWPiW0uIOnoxG9fzOiLzYHYJ7fgfQGoOF2OwQphQySY8WOy99oddonBaq52A")
PASSWORD = os.environ.get("OPENHAB_PASSWORD", "")

def get_auth_header():
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}

def make_request(endpoint):
    try:
        req = urllib.request.Request(f"{BASE_URL}{endpoint}")
        req.add_header("Authorization", get_auth_header()["Authorization"])
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except Exception as e:
        return None

def healthcheck():
    print("🏥 openHAB System Health Report")
    print("=" * 50)
    
    # 1. Server connectivity
    print("\n📡 Server Status:")
    try:
        items = make_request("/rest/items")
        if items:
            print(f"  ✅ Server online")
            print(f"  ✅ API accessible")
        else:
            print(f"  ❌ Server unreachable")
            return
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return
    
    # 2. Item statistics
    print(f"\n📦 Item Statistics:")
    print(f"  Total items: {len(items)}")
    
    types = {}
    for item in items:
        t = item.get('type', 'Unknown')
        types[t] = types.get(t, 0) + 1
    
    print(f"  Item types:")
    for itype, count in sorted(types.items(), key=lambda x: -x[1])[:10]:
        print(f"    • {itype}: {count}")
    
    # 3. Things status
    print(f"\n🔌 Things Status:")
    things = make_request("/rest/things")
    if things:
        statuses = {}
        for thing in things:
            status = thing.get('statusInfo', {}).get('status', 'UNKNOWN')
            statuses[status] = statuses.get(status, 0) + 1
        
        print(f"  Total things: {len(things)}")
        for status, count in sorted(statuses.items()):
            icon = "✅" if status == "ONLINE" else "⚠️" if status == "UNKNOWN" else "❌"
            print(f"    {icon} {status}: {count}")
    
    # 4. Bridge status (Velux KLF200)
    print(f"\n🌉 Bridge Status:")
    bridge_state = make_request("/rest/items/Velux_KLF200_Bridge_Bridge_State")
    if bridge_state:
        state = bridge_state.get('state', 'UNKNOWN')
        print(f"  Velux KLF200: {state}")
        if "IDLE" in state:
            print(f"    ✅ Bridge idle and ready")
        else:
            print(f"    ⚠️ Bridge state: {state}")
    
    # 5. Offline things alert
    print(f"\n⚠️  Offline/Problem Devices:")
    offline_count = 0
    uninitialized_count = 0
    for thing in things:
        status = thing.get('statusInfo', {}).get('status', 'ONLINE')
        if status == 'OFFLINE':
            offline_count += 1
            label = thing.get('label', thing.get('uid', 'Unknown'))
            print(f"  ⚠️  {label}: OFFLINE")
        elif status == 'UNINITIALIZED':
            uninitialized_count += 1
    if offline_count == 0 and uninitialized_count == 0:
        print(f"  ✅ All devices online")
    else:
        if offline_count > 0:
            print(f"  ⚠️  OFFLINE devices: {offline_count}")
        if uninitialized_count > 0:
            print(f"  ℹ️  UNINITIALIZED devices: {uninitialized_count}")
    
    # 6. Rules status (NEW LOGIC PER USER DIRECTIVE)
    print(f"\n⚙️  Rules Status:")
    rules = make_request("/rest/rules")
    if rules:
        idle_count = 0
        uninitialized_disabled_count = 0
        warning_count = 0
        warning_details = []
        for r in rules:
            status_obj = r.get('status', {})
            if isinstance(status_obj, dict):
                status = status_obj.get('status', 'UNKNOWN')
                detail = status_obj.get('statusDetail', 'NONE')
            else:
                status = str(status_obj)
                detail = 'NONE'
            if status == 'IDLE':
                idle_count += 1
            elif status == 'UNINITIALIZED' and detail == 'DISABLED':
                uninitialized_disabled_count += 1
            else:
                warning_count += 1
                warning_details.append(f"{r.get('name', '(no name)')}: status={status}, detail={detail}")
        print(f"  Total rules: {len(rules)}")
        print(f"  ✅ IDLE (waiting for triggers): {idle_count}")
        print(f"  ✅ UNINITIALIZED + DISABLED (intentionally off): {uninitialized_disabled_count}")
        if warning_count:
            print(f"  ⚠️  Other statuses (check): {warning_count}")
            for w in warning_details[:5]:  # show first 5
                print(f"      - {w}")
            if warning_count > 5:
                print(f"      ... and {warning_count - 5} more")
    else:
        print(f"  ❌ Could not fetch rules")
    
    print("\n" + "=" * 50)
    print("✅ Health check complete")

if __name__ == "__main__":
    healthcheck()
```

### 2. Monitor Specific Thing Status

```bash
#!/bin/bash
BASE_URL="${OPENHAB_BASE_URL:-http://192.168.1.10:8080}"
USER="${OPENHAB_USERNAME:-oh.Hermes.m3aG9XZppfjiYo4noYlRVISNE6TWPiW0uIOnoxG9fzOiLzYHYJ7fgfQGoOF2OwQphQySY8WOy99oddonBaq52A}"

THING_UID="${1:-Velux_KLF200}"

echo "🔍 Thing Status Report: $THING_UID"
echo "====================================="

curl -s -u "$USER:" "$BASE_URL/rest/things" | python3 << EOF
import sys, json

things = json.load(sys.stdin)
target = "$THING_UID"

for thing in things:
    uid = thing.get('uid', '')
    if target.lower() in uid.lower():
        print(f"UID: {uid}")
        print(f"Label: {thing.get('label', 'N/A')}")
        print(f"Status: {thing.get('statusInfo', {}).get('status', 'UNKNOWN')}")
        print(f"Bridge: {thing.get('bridge', 'N/A')}")
        print(f"Type: {thing.get('thingTypeUID', 'N/A')}")
        print(f"Config: {json.dumps(thing.get('configuration', {}), indent=2)}")
        break
else:
    print(f"Thing '{target}' not found")
EOF
```

### 3. Advanced Diagnostics: Shutters, Gateways & Batteries

```python
#!/usr/bin/env python3
"""
Advanced health check:
- Fibaro shutters accessibility and status (must be rolled up)
- Zigbee and Z-Wave gateway status
- Battery levels (alert on zero or inaccessible)
"""
import json
import urllib.request
import base64
import re

BASE_URL = os.environ.get("OPENHAB_BASE_URL", "http://192.168.1.10:8080")
USERNAME = os.environ.get("OPENHAB_USERNAME", "oh.Hermes.m3aG9XZppfjiYo4noYlRVISNE6TWPiW0uIOnoxG9fzOiLzYHYJ7fgfQGoOF2OwQphQySY8WOy99oddonBaq52A")
PASSWORD = os.environ.get("OPENHAB_PASSWORD", "")

def make_request(endpoint):
    try:
        credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
        req = urllib.request.Request(f"{BASE_URL}{endpoint}")
        req.add_header("Authorization", f"Basic {credentials}")
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"  ❌ API Error: {e}")
        return None

print("🔍 Advanced Health Diagnostics")
print("=" * 60)

items = make_request("/rest/items")
things = make_request("/rest/things")

if not items:
    print("Failed to fetch items")
    exit(1)

# ============================================================================
# 1. FIBARO SHUTTERS CHECK
# ============================================================================
print("\n🪟 Fibaro Roller Shutters Status:")
print("-" * 60)

fibaro_shutters = [item for item in items if 'fibaro' in item.get('name', '').lower() and 'roller' in item.get('name', '').lower()]
shutter_positions = [item for item in fibaro_shutters if 'position' in item.get('name', '').lower() or item.get('type') == 'Rollershutter']

if not shutter_positions:
    print("  ⚠️  No Fibaro shutters found")
else:
    print(f"  Total Fibaro shutters: {len(shutter_positions)}")
    
    not_rolled_up = []
    inaccessible = []
    
    for shutter in sorted(shutter_positions, key=lambda x: x.get('name')):
        name = shutter.get('name')
        state = shutter.get('state', 'UNKNOWN')
        label = shuttle.get('label', name)
        
        # Check if accessible
        if state == 'NULL' or state is None or state == 'UNKNOWN':
            inaccessible.append((name, label, state))
            print(f"  ❌ INACCESSIBLE: {label} ({name}) — State: {state}")
        # Check if rolled up (0% or UP is fully rolled up)
        elif state in ['0', '0.0', 'UP']:
            print(f"  ✅ ROLLED UP: {label} — {state}")
        else:
            not_rolled_up.append((name, label, state))
            print(f"  ⚠️  NOT ROLLED UP: {label} ({name}) — Position: {state}%")
    
    if not_rolled_up:
        print(f"\n  🚨 ALERT: {len(not_rolled_up)} shutter(s) not fully rolled up:")
        for name, label, state in not_rolled_up:
            print(f"     • {label}: {state}%")
    
    if inaccessible:
        print(f"\n  🚨 ALERT: {len(inaccessible)} shutter(s) inaccessible:")
        for name, label, state in inaccessible:
            print(f"     • {label} ({name}): {state}")

# ============================================================================
# 2. GATEWAY STATUS CHECK (Zigbee & Z-Wave)
# ============================================================================
print("\n🌐 Gateway Status (Zigbee & Z-Wave):")
print("-" * 60)

if not things:
    print("  ⚠️  Could not fetch things data")
else:
    gateways = {
        'zigbee': [],
        'zwave': [],
        'mqtt': [],
        'modbus': [],
        'viessmann': [],
        'sma': [],
        'other': []
    }
    
    for thing in things:
        uid = thing.get('uid', '').lower()
        label = thing.get('label', uid)
        status = thing.get('statusInfo', {}).get('status', 'UNKNOWN')
        
        # Match by label name (more reliable than UID patterns)
        if 'zigbee phoscon' in label.lower() or 'phoscon' in uid.lower():
            gateways['zigbee'].append((label, status))
        elif 'z-wave' in label.lower() or 'usb controller' in label.lower():
            # Exclude test Z-Wave nodes
            if 'node 019' not in label.lower() and 'node 014' not in label.lower():
                gateways['zwave'].append((label, status))
        elif 'mqtt' in label.lower() or 'mqtt' in uid.lower():
            gateways['mqtt'].append((label, status))
        elif 'modbus' in label.lower() or 'friwa' in label.lower():
            gateways['modbus'].append((label, status))
        elif 'viessmann' in label.lower() or 'vitotronic' in label.lower():
            gateways['viessmann'].append((label, status))
        elif 'sma' in label.lower() and ('bridge' in label.lower() or 'modbus' in uid.lower()):
            gateways['sma'].append((label, status))
    
    # Zigbee
    print("\n  Zigbee Gateway:")
    if gateways['zigbee']:
        for label, status in gateways['zigbee']:
            icon = "✅" if status == "ONLINE" else "❌"
            print(f"    {icon} {label}: {status}")
    else:
        print("    ⚠️  No Zigbee gateway found")
    
    # Z-Wave
    print("\n  Z-Wave Gateway:")
    if gateways['zwave']:
        for label, status in gateways['zwave']:
            icon = "✅" if status == "ONLINE" else "❌"
            print(f"    {icon} {label}: {status}")
    else:
        print("    ⚠️  No Z-Wave gateway found")
    
    # MQTT Broker
    print("\n  MQTT Broker:")
    if gateways['mqtt']:
        for label, status in gateways['mqtt']:
            icon = "✅" if status == "ONLINE" else "❌"
            print(f"    {icon} {label}: {status}")
    else:
        print("    ⚠️  No MQTT broker found")
    
    # Modbus FriWaSta
    print("\n  Modbus FriWaSta Bridge:")
    if gateways['modbus']:
        for label, status in gateways['modbus']:
            icon = "✅" if status == "ONLINE" else "❌"
            print(f"    {icon} {label}: {status}")
    else:
        print("    ⚠️  No Modbus FriWaSta bridge found")
    
    # Viessmann Vitotronic
    print("\n  Viessmann Vitotronic (MQTT-based):")
    if gateways['viessmann']:
        for label, status in gateways['viessmann']:
            icon = "✅" if status == "ONLINE" else "❌"
            print(f"    {icon} {label}: {status}")
    else:
        print("    ⚠️  No Viessmann Vitotronic bridge found")
    
    # SMA Bridge
    print("\n  SMA Bridge (Modbus):")
    if gateways['sma']:
        for label, status in gateways['sma']:
            icon = "✅" if status == "ONLINE" else "❌"
            print(f"    {icon} {label}: {status}")
    else:
        print("    ⚠️  No SMA bridge found")

# ============================================================================
# 3. BATTERY LEVELS CHECK
# ============================================================================
print("\n🔋 Battery Level Report:")
print("-" * 60)

battery_items = [item for item in items if 'battery' in item.get('name', '').lower()]

print(f"\n  Total battery items: {len(battery_items)}")

critical_batteries = []
zero_batteries = []
inaccessible_batteries = []
low_batteries = []

for battery in battery_items:
    name = battery.get('name')
    state = battery.get('state', 'UNKNOWN')
    label = battery.get('label', name)
    
    try:
        # Try to parse as float
        if state == 'NULL' or state is None or state == 'UNKNOWN':
            inaccessible_batteries.append((label, name, state))
        else:
            # Extract numeric value (handle formats like "80", "80.0", "80 %")
            match = re.search(r'(\\d+\\.?\\d*)', str(state))
            if match:
                level = float(match.group(1))
                if level == 0:
                    zero_batteries.append((label, name, state))
                elif level < 20:
                    low_batteries.append((label, name, level))
            else:
                inaccessible_batteries.append((label, name, state))
    except Exception as e:
        inaccessible_batteries.append((label, name, f"Error: {e}"))

# Report critical issues first
if zero_batteries:
    print(f"\n  🚨 CRITICAL - Zero Battery (0%):")
    for label, name, state in zero_batteries:
        # Ignore SMA Battery Discharge — it's designed to go to zero
        if 'sma' not in name.lower() or 'discharge' not in name.lower():
            print(f"    ❌ {label} ({name}): {state}")
        else:
            print(f"    ✅ {label} ({name}): {state} (Normal — SMA battery discharge cycles)")
    if all('sma' in n.lower() and 'discharge' in n.lower() for _, n, _ in zero_batteries):
        zero_batteries = []  # Clear the alert if only SMA discharge

if inaccessible_batteries:
    print(f"\n  ⚠️  INACCESSIBLE - Cannot read battery level:")
    for label, name, state in inaccessible_batteries:
        print(f"    ❓ {label} ({name}): {state}")

if low_batteries:
    print(f"\n  ⚠️  LOW - Battery level < 20%:")
    for label, name, level in sorted(low_batteries, key=lambda x: x[2]):
        print(f"    🔻 {label} ({name}): {level}%")

# Summary
if not zero_batteries and not inaccessible_batteries and not low_batteries:
    print(f"\n  ✅ All {len(battery_items)} batteries are in good condition")

# ============================================================================
# 4. OFFLINE & UNINITIALIZED THINGS CHECK
# ============================================================================
print("\n📴 Offline & Uninitialized Things:")
print("-" * 60)

offline_things = []
uninitialized_things = []

for thing in things:
    uid = thing.get('uid')
    label = thing.get('label', uid)
    status_info = thing.get('statusInfo', {})
    
    # Check for OFFLINE status
    if status_info and status_info.get('status') == 'OFFLINE':
        offline_things.append((label, uid, status_info.get('statusDetail', 'UNKNOWN')))
    
    # Check for uninitialized things
    if status_info and 'UNINITIALIZED' in str(status_info.get('status', '')).upper():
        uninitialized_things.append((label, uid, status_info.get('statusDetail', 'UNKNOWN')))

if offline_things:
    print(f"\n  ❌ OFFLINE Things ({len(offline_things)}):")
    for label, uid, detail in sorted(offline_things)[:10]:
        print(f"    • {label} ({uid}): {detail}")
    if len(offline_things) > 10:
        print(f"    ... and {len(offline_things) - 10} more")
else:
    print(f"\n  ✅ No offline things detected")

if uninitialized_things:
    print(f"\n  ⚠️  UNINITIALIZED Things ({len(uninitialized_things)}):")
    for label, uid, detail in sorted(uninitialized_things)[:10]:
        print(f"    • {label} ({uid}): {detail}")
    if len(uninitialized_things) > 10:
        print(f"    ... and {len(uninitialized_things) - 10} more")
else:
    print(f"\n  ✅ No uninitialized things detected")

# ============================================================================
# 5. OPENHAB LOG ERRORS CHECK (10 second observation via web log-viewer)
# ============================================================================
print("\n📋 openHAB Log Error Scan (20 sec observation):")
print("-" * 60)

log_errors = {}
try:
    print("  Observing logs from http://192.168.1.10:8080/developer/log-viewer ...")
    
    # Fetch from web log viewer
    log_viewer_url = "http://192.168.1.10:8080/developer/log-viewer"
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    
    req = urllib.request.Request(log_viewer_url)
    req.add_header("Authorization", f"Basic {credentials}")
    
    # Wait 20 seconds while observing
    time.sleep(20)
    
    # Fetch log data
    with urllib.request.urlopen(req, timeout=10) as response:
        log_content = response.read().decode('utf-8')
    
    # Try to parse log entries from HTML/JSON response
    # Look for error patterns in the response
    error_patterns = ['ERROR', 'WARN', 'Exception', 'FAIL', 'error', 'failed']
    
    # Parse lines that contain errors
    for line in log_content.split('\\n'):
        if any(pattern in line for pattern in error_patterns):
            # Clean up the line
            clean_line = line.strip()
            if clean_line and len(clean_line) > 10:  # Skip empty/tiny lines
                # Extract meaningful error message (first 80 chars)
                error_type = clean_line[:80]
                log_errors[error_type] = log_errors.get(error_type, 0) + 1
    
    if log_errors:
        print(f"\n  🚨 Detected Recurring Errors ({len(log_errors)} unique types):")
        for error, count in sorted(log_errors.items(), key=lambda x: -x[1])[:10]:
            print(f"    • {error} (x{count})")
    else:
        print(f"\n  ✅ No errors detected in recent logs")
except urllib.error.HTTPError as e:
    if e.code == 401:
        print(f"  ⚠️  Authentication failed (401) — check API credentials")
    else:
        print(f"  ⚠️  HTTP {e.code} error accessing log viewer")
except Exception as e:
    print(f"  ⚠️  Could not fetch logs: {e}")
    print(f"     Try: curl -u 'username:' http://192.168.1.10:8080/developer/log-viewer")

print("\n" + "=" * 60)
print("✅ Advanced diagnostics complete")
```

## Cron Job: Regular Health Monitoring

Monitor every hour and alert on issues:

```bash
#!/bin/bash
# Run: hermes cron create --schedule \"0 * * * *\" --prompt \"check openhab health\"

HEALTH_REPORT=$(python3 << 'EOF'
# Insert Full System Health Status script here
EOF
)

# Log to file
echo \"[$(date)] Health Check:\" >> ~/.hermes/logs/openhab-health.log
echo \"$HEALTH_REPORT\" >> ~/.hermes/logs/openhab-health.log

# Alert if issues detected
if echo \"$HEALTH_REPORT\" | grep -q \"❌\"; then
    echo \"⚠️ openHAB health issues detected\"
    # Could send to Telegram, email, etc.
fi
```

## Rules Health Check Logic

When evaluating rule health in the health check, the following states are considered **OK**:

| Rule Status    | Status      | Reason                                                               |
|----------------|-------------|----------------------------------------------------------------------|
| `IDLE`         | ✅ IDLE     | Rule is enabled and monitoring/waiting for triggers (or disabled but idle — still ready) |
| `UNINITIALIZED`| ✅ INACTIVE | **Only** when accompanied by `statusDetail: "DISABLED"` — indicates intentional deactivation by user |
| `INITIALIZING` | ⚠️ WARNING  | Rule is currently initializing (should transition quickly)           |
| `RUNNING`      | ⚠️ WARNING  | Rule is currently executing (could be normal if short-lived, but prolonged may indicate issue) |
| `FAILED`       | ❌ ERROR    | Rule has failed and requires intervention                            |
| `WARNING`      | ⚠️ WARNING  | Rule has produced a warning and should be checked                    |
| `ERROR`        | ❌ ERROR    | Rule has failed and should be checked                                |

**Key insight:** Rules showing `"idle"` status are ready and functional — they're simply not currently executing. An idle rule is equivalent to an enabled rule that's waiting for its trigger condition. Therefore, idle rules should be counted as active/healthy.

Rules showing `"UNINITIALIZED"` with `"statusDetail": "DISABLED"` are intentionally turned off by the user and are considered healthy.

All other status combinations indicate a potential issue and should be investigated.

**Implementation:**
```python
# Count healthy rules (IDLE OR UNINITIALIZED+DISABLED)
healthy_rules = sum(1 for r in rules if 
                    (r.get('status', {}).get('status') == 'IDLE') or
                    (r.get('status', {}).get('status') == 'UNINITIALIZED' and 
                     r.get('status', {}).get('statusDetail') == 'DISABLED'))
# Count warning/error rules
issue_rules = len(rules) - healthy_rules
```

## Troubleshooting Guide

| Symptom | Cause | Solution |
|---------|-------|----------|
| Server offline | Network issue or service down | Check network connectivity, restart openHAB service |
| Auth failed (401) | Invalid credentials | Verify API token in env vars |
| Things OFFLINE | Device connectivity lost | Check device power, WiFi signal, Zigbee/Z-Wave range |
| Items NULL state | Binding error or item misconfigured | Check binding logs, rediscover things |
| Bridge OFFLINE | KLF200 bridge connection failed | Power cycle KLF200, check network connection |
| High latency | Server overload or network congestion | Monitor CPU/memory, optimize rules |
| Rules showing unexpected status | See Rules Health Check Logic above | Investigate based on status/detail |

## Key Endpoints for Health Monitoring

- `/rest/items` — All items and their states
- `/rest/things` — All devices and their status
- `/rest/rules` — Automation rules (with nested status object)
- `/rest/inbox` — Discovery inbox (pending things)
- `/rest/config/services` — System services status
- `/rest/systeminfo` — Version, uptime, etc.

## Best Practices

1. **Regular health checks** — Run hourly or daily
2. **Monitor bridge status** — Velux KLF200 is critical for window control
3. **Watch for NULL states** — Often indicates binding or device issues
4. **Track offline devices** — Alert when devices go offline unexpectedly
5. **Review rules** — Ensure automation rules are enabled and working (or intentionally disabled)
6. **Keep logs** — Save health reports for troubleshooting trends

## Integration with Hermes

Use in cron jobs or as a scheduled task to get regular status updates via Telegram or email.

## Using openHAB API for Control and Queries

While this skill focuses on health monitoring, the same openHAB REST API can be used to control devices and retrieve states in response to user commands like:

- **Turn on a light:** `PUT /rest/items/<item_name>` with payload `ON`
- **Get temperature:** `GET /rest/items/<item_name>` → returns state
- **Get CO2 level:** `GET /rest/items/<co2_item>` → state
- **Get weather forecast:** Query a weather binding item (e.g., `GET /rest/items/Weather_Forecast`)
- **Get battery level:** `GET /rest/items/<battery_item>` → state (percent)

These requests can be executed via Hermes using the `terminal` tool with `curl` or via the `execute_code` script using `make_request` (as shown in the healthcheck examples). For example:

```python
# Example: Get temperature from a sensor
item = make_request("/rest/items/Sensor_Temperature_LivingRoom")
if item:
    print(f"Temperature: {item.get('state')} {item.get('unit', '')}")
```

Remember to include proper authentication (Basic Auth with username and empty password as configured in the skill). Always verify the item name exists in openHAB (you can list items via `/rest/items`).

When you say phrases like "turn on light..." or "get me the temperature in room/device...", Hermes should interpret these as requests to query or modify the openHAB API accordingly.