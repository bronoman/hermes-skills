# openHAB REST API Examples for Device Control and Querying

This file provides common examples of using the openHAB REST API to control devices and retrieve states, which can be used when interpreting natural language commands like "turn on light..." or "get me the temperature in room/device...".

## Environment
- URL: `OPENHAB_BASE_URL` environment variable 

## Authentication
All requests require Basic Auth with:

- Username: `OPENHAB_USERNAME` environment variable
- Password: `OPENHAB_PASSWORD` environment variable (can be empty if not set)

Example curl authentication:
```bash
# Replace <token> with your openHAB API token (password is empty)
curl -u "<token>:" "http://openhab-host:8080/rest/items/Item_Name"
```

## Common Operations

### 1. Get Item State
Retrieve the current state of any item (sensor, switch, etc.)

**GET** `/rest/items/<item_name>`

**Response:**
```json
{
  "link": "http://openhab-host:8080/rest/items/Item_Name",
  "state": "ON",
  "type": "Switch",
  "name": "Item_Name",
  "label": "Living Room Light",
  ...
}
```

**Examples:**
- Get temperature: `GET /rest/items/Sensor_Temperature_LivingRoom`
- Get humidity: `GET /rest/items/Sensor_Humidity_Bathroom`
- Get CO2 level: `GET /rest/items/Sensor_CO2_Kitchen`
- Get light state: `GET /rest/items/Light_LivingRoom_Ceiling`

### 2. Send Command to Item
Change the state of a controllable item (light, switch, etc.)

**PUT** `/rest/items/<item_name>`
**Headers:** `Content-Type: text/plain`
**Body:** Command string (e.g., "ON", "OFF", "INCREASE", "DECREASE", or a percent value for dimmers)

**Examples:**
- Turn on light: `PUT /rest/items/Light_LivingRoom_Ceiling` with body "ON"
- Turn off light: `PUT /rest/items/Light_LivingRoom_Ceiling` with body "OFF"
- Set dimmer to 50%: `PUT /rest/items/Dimmer_Lighting_Table` with body "50"
- Increase thermostat: `PUT /rest/items/Thermostat_Setpoint_LivingRoom` with body "INCREASE"
- Decrease thermostat: `PUT /rest/items/Thermostat_Setpoint_LivingRoom` with body "DECREASE"

### 3. Get Item Metadata
Retrieve additional information about an item (unit, labels, etc.)

**GET** `/rest/items/<item_name>/metadata`

### 4. Get All Items of a Specific Type
Useful for discovering available sensors or actuators

**GET** `/rest/items?type=<item_type>`

**Common item types:**
- `Number:Temperature` - Temperature sensors
- `Number:Dimensionless` - Humidity, CO2, etc. (often)
- `Switch` - On/off devices
- `Dimmer` - Dimmable lights
- `Color` - RGB lights
- `Contact` - Door/window sensors
- `Rollershutter` - Blinds/shutters

**Example:** Get all temperature sensors
```bash
curl -u "<token>:" "http://openhab-host:8080/rest/items?type=Number:Temperature"
```

### 5. Discover Items by Label or Name
When you know part of an item's label or name but not the exact item name

First get all items, then filter:
```bash
# Get all items and filter for those containing "temperature" in label (case-insensitive)
curl -s -u "<token>:" "http://openhab-host:8080/rest/items" | \
  python3 -c "import sys, json; items=json.load(sys.stdin); \
  [print(i['name'], i['label'], i.get('state')) for i in items if 'temperature' in i.get('label','').lower()]"
```

## Natural Language Command Mapping

When interpreting user phrases, use these patterns:

| User Phrase Pattern        | API Action                              | Example                                                                      |
|----------------------------|-----------------------------------------|------------------------------------------------------------------------------|
| "turn on [device]"         | PUT /rest/items/<item> with "ON"        | "turn on kitchen light" → PUT /rest/items/Light_Kitchen with "ON"            |
| "turn off [device]"        | PUT /rest/items/<item> with "OFF"       | "turn off bedroom lamp" → PUT /rest/items/Light_Bedroom with "OFF"           |
| "set [device] to [value]%" | PUT /rest/items/<item> with "<value>"   | "set bedroom light to 75%" → PUT /rest/items/Light_Bedroom with "75"         |
| "get [sensor] reading"     | GET /rest/items/<item>                  | "get temperature living room" → GET /rest/items/Sensor_Temp_LR               |
| "what is [sensor]"         | GET /rest/items/<item>                  | "what is humidity bathroom" → GET /rest/items/Sensor_Hum_Bath                |
| "is [device] on?"          | GET /rest/items/<item> then check state | "is kitchen light on?" → GET /rest/items/Light_Kitchen, check if state=="ON" |
| "increase [device]"        | PUT /rest/items/<item> with "INCREASE"  | "increase thermostat" → PUT /rest/items/Thermostat_Setpoint with "INCREASE"  |
| "decrease [device]"        | PUT /rest/items/<item> with "DECREASE"  | "decrease thermostat" → PUT /rest/items/Thermostat_Setpoint with "DECREASE"  |

## Error Handling
- **401 Unauthorized**: Check credentials in environment variables
- **404 Not Found**: Item name doesn't exist - verify with GET /rest/items
- **405 Method Not Allowed**: Item doesn't accept commands (check item type)
- **500 Internal Server Error**: openHAB server error - check openHAB logs

## Examples in Python (using the skill's make_request pattern)

```python
# Get temperature from a sensor
def get_temperature(sensor_name):
    item = make_request(f"/rest/items/{sensor_name}")
    if item and 'state' in item:
        return f"{item['state']} °C"
    return "Unable to read temperature"

# Turn on a light
def turn_on_light(light_name):
    result = make_request(f"/rest/items/{light_name}", method='PUT', data='ON')
    if result is None:  # Success returns None
        return f"Turned on {light_name}"
    return f"Failed to turn on {light_name}: {result}"

# Set dimmer level
def set_dimmer_level(light_name, percent):
    result = make_request(f"/rest/items/{light_name}", method='PUT', data=str(percent))
    if result is None:
        return f"Set {light_name} to {percent}%"
    return f"Failed to set dimmer: {result}"

# Check if a switch is on
def is_switch_on(switch_name):
    item = make_request(f"/rest/items/{switch_name}")
    if item and item.get('state') == 'ON':
        return True
    return False
```
