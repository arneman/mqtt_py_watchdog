# MQTT Python Watchdog

A reliable monitoring tool that watches MQTT topics for activity and triggers actions when devices go silent.

## Features

- Monitor multiple MQTT topics for activity
- Configurable timeout intervals per device
- Flexible actions when timeouts occur:
  - Execute shell commands
  - Send MQTT alert messages
- Secure MQTT connection support with username/password

## Installation

1. Create a Python virtual environment:
```bash
python -m venv .venv
```

2. Activate the virtual environment:
```bash
source .venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Copy config.json and customize it:
```bash
cp config.json.example config.json
```

See 'Running as a System Service' below if you want to run it as systemd service.

## Configuration

Configure the watchdog in `config.json`:

```json
{
    "log_level": "INFO",    // DEBUG, INFO, WARNING, ERROR, CRITICAL
    "mqtt": {
        "broker": "localhost",
        "port": 1883,
        "username": "mqtt_user",
        "password": "your_password"
    },
    "watchdogs": [
        {
            "name": "Device Name",         // Friendly name for the watchdog
            "topic": "device/heartbeat",   // Topic to monitor
            "interval": 60,                // Timeout in seconds
            "action_cmd": "/bin/systemctl restart sensor_service",       // Shell command to execute, use full path (optional)
        },
        {
            "name": "Device Name 2",       // Friendly name for the watchdog
            "topic": "device2/heartbeat",  // Topic to monitor
            "interval": 90,                // Timeout in seconds
            "action_mqtt_topic": "alerts/device2",  // Alert topic (optional)
            "action_mqtt_payload": "{\"status\": \"offline\"}"  // Alert message
        }
    ]
}
```

## Running as a System Service

2. Create installation directory and copy files:
```bash
cd /opt
git clone https://github.com/arneman/mqtt_py_watchdog.git
cd mqtt_py_watchdog
```

3. Set up the virtual environment in the installation directory:
```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

4. Install and start the service:
```bash
sudo cp mqtt-py-watchdog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mqtt-py-watchdog
sudo systemctl start mqtt-py-watchdog
```

5. Check service status:
```bash
sudo systemctl status mqtt-py-watchdog
```

Service logs can be viewed with:
```bash
sudo journalctl -u mqtt-py-watchdog -f
```

## Commercial Use

For commercial licensing please contact:
- Email: arne@drees.one

If you want to thank me:
- PayPal: https://www.paypal.me/arnedrees

## License

See LICENSE file for details.
