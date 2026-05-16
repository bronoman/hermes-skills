#!/usr/bin/env python3
"""openHAB Full System Health Report"""
import json, urllib.request, base64, sys, os
from collections import Counter

base_url = os.environ.get("OPENHAB_BASE_URL")
username = os.environ.get("OPENHAB_USERNAME")
password = os.environ.get("OPENHAB_PASSWORD")

if not base_url or not username or not password:
    print("❌ Missing openHAB credentials. Run: hermes skills configure openhab")
    sys.exit(1)

def api(endpoint):
    try:
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        req = urllib.request.Request(f"{base_url}{endpoint}")
        req.add_header("Authorization", f"Basic {credentials}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"API error: {e}")
        return None

# ... rest of your script stays exactly the same

print("🏥 openHAB System Health Report")
print("=" * 50)

# 1. Server connectivity
print("\n🌐 Server: ", end="")
try:
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req, timeout=3) as resp:
        print(f"✅ ONLINE ({resp.status})")
except Exception as e:
    print(f"❌ OFFLINE ({e})")
    sys.exit(1)

# 2. Items
items = api("/rest/items")
if items is None:
    print("❌ API call failed — check auth")
    sys.exit(1)

print(f"\n📦 Items: {len(items)}")
types = Counter(i.get('type', 'Unknown') for i in items)
#for t, c in types.most_common(10):
#    print(f"  • {t}: {c}")

# 3. Things
things = api("/rest/things") or []
print(f"\n🔌 Things: {len(things)}")
statuses = Counter(t.get('statusInfo', {}).get('status', 'UNKNOWN') for t in things)
for status, count in sorted(statuses.items()):
    icon = "✅" if status == "ONLINE" else "⚠️" if status == "UNKNOWN" else "❌"
    print(f"  {icon} {status}: {count}")

offline = [t for t in things if t.get('statusInfo', {}).get('status') == 'OFFLINE']
uninit = [t for t in things if t.get('statusInfo', {}).get('status') == 'UNINITIALIZED']
if offline:
    print(f"\n❌ OFFLINE ({len(offline)}):")
    for t in offline[:15]:
        print(f"  • {t.get('label', t.get('uid'))}")
if uninit:
    print(f"\n⚠️  UNINITIALIZED ({len(uninit)}):")
    for t in uninit[:15]:
        print(f"  • {t.get('label', t.get('uid'))}")
if not offline and not uninit:
    print("\n✅ All devices online")

# 4. Rules
rules = api("/rest/rules") or []
print(f"\n⚙️  Rules: {len(rules)}")
idle = sum(1 for r in rules if r.get('status', {}).get('status') == 'IDLE')
disabled = sum(1 for r in rules if r.get('status', {}).get('status') == 'UNINITIALIZED'
               and r.get('status', {}).get('statusDetail') == 'DISABLED')
issues = len(rules) - idle - disabled
print(f"  ✅ IDLE: {idle}")
print(f"  ✅ DISABLED: {disabled}")
if issues:
    print(f"  ⚠️  ISSUES: {issues}")
    for r in rules:
        s = r.get('status', {}).get('status', 'UNKNOWN')
        d = r.get('status', {}).get('statusDetail', 'NONE')
        if s not in ('IDLE',) and not (s == 'UNINITIALIZED' and d == 'DISABLED'):
            print(f"    - {r.get('name', '?')}: {s}/{d}")

# 5. Batteries
batteries = [i for i in items if 'battery' in i.get('name', '').lower()]
if batteries:
    print(f"\n🔋 Batteries: {len(batteries)}")
    low, zero, inaccessible = [], [], []
    for b in batteries:
        state = b.get('state', 'UNKNOWN')
        label = b.get('label', b.get('name'))
        if state in ('NULL', None, 'UNKNOWN'):
            inaccessible.append(label)
        else:
            m = re.search(r'(\d+\.?\d*)', str(state))
            if m:
                level = float(m.group(1))
                if level == 0 and 'sma' not in b['name'].lower():
                    zero.append((label, level))
                elif level < 20:
                    low.append((label, level))
    if zero:
        print(f"  🚨 ZERO: {', '.join(l for l,_ in zero)}")
    if low:
        print(f"  ⚠️  LOW: {', '.join(f'{l}:{v}%' for l,v in low)}")
    if inaccessible:
        print(f"  ❓ INACCESSIBLE: {', '.join(inaccessible)}")
    if not zero and not low and not inaccessible:
        print("  ✅ All batteries OK")

# 6. Gateway status
print("\n🌉 Gateways:")
gateways = {'zigbee': [], 'zwave': [], 'mqtt': [], 'modbus': [], 'viessmann': [], 'sma': []}
for thing in things:
    label = thing.get('label', '').lower()
    uid = thing.get('uid', '').lower()
    status = thing.get('statusInfo', {}).get('status', 'UNKNOWN')
    if 'zigbee' in label or 'phoscon' in uid:
        gateways['zigbee'].append((thing.get('label'), status))
    elif 'z-wave' in label or 'usb controller' in label:
        if 'node 019' not in label and 'node 014' not in label:
            gateways['zwave'].append((thing.get('label'), status))
    elif 'mqtt' in label or 'mqtt' in uid:
        gateways['mqtt'].append((thing.get('label'), status))
    elif 'modbus' in label or 'friwa' in label:
        gateways['modbus'].append((thing.get('label'), status))
    elif 'viessmann' in label or 'vitotronic' in label:
        gateways['viessmann'].append((thing.get('label'), status))
    elif 'sma' in label and 'bridge' in label:
        gateways['sma'].append((thing.get('label'), status))

for gw_type, devices in gateways.items():
    if devices:
        for label, status in devices:
            icon = "✅" if status == "ONLINE" else "❌"
            print(f"  {icon} {gw_type.upper()}: {label} ({status})")
    else:
        print(f"  ⚠️  {gw_type.upper()}: Not found")

# 7. Fibaro shutters
shutters = [i for i in items if 'fibaro' in i.get('name', '').lower()
            and 'roller' in i.get('name', '').lower()
            and ('position' in i.get('name', '').lower() or i.get('type') == 'Rollershutter')]
if shutters:
    print("\n🪟 Fibaro Roller Shutters:")
    for s in sorted(shutters, key=lambda x: x.get('name')):
        state = s.get('state', 'UNKNOWN')
        label = s.get('label', s.get('name'))
        if state in ('NULL', None, 'UNKNOWN'):
            print(f"  ❌ INACCESSIBLE: {label}")
        elif state in ('0', '0.0', 'UP'):
            print(f"  ✅ ROLLED UP: {label}")
        else:
            print(f"  ⚠️  NOT ROLLED UP: {label} — {state}%")

print("\n" + "=" * 50)
print("✅ Health check complete")
