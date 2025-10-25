import paho.mqtt.client as mqtt
import threading
import json
import subprocess
import sys
import logging

# --- Global Variables ---
CONFIG_FILE = "config.json"
WATCHDOGS = {}  # Stores all timer objects: {topic: threading.Timer object}
CLIENT = None
CONFIG = None


# --- Logging Configuration ---
def setup_logging():
    """Configures logging with the level from the configuration file."""
    log_level_str = CONFIG.get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info(f"Logging configured with level: {log_level_str}")


logger = logging.getLogger(__name__)
CONFIG_FILE = "config.json"
WATCHDOGS = {}  # Stores all timer objects: {topic: threading.Timer object}


logger = logging.getLogger(__name__)
CONFIG_FILE = "config.json"
WATCHDOGS = {}  # Speichert alle Timer-Objekte: {topic: threading.Timer object}
CLIENT = None
CONFIG = None

# --- Helper Functions ---


def load_config():
    """Loads the configuration from the JSON file."""
    global CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            CONFIG = json.load(f)
        setup_logging()
        logger.info("Configuration loaded successfully.")
    except FileNotFoundError:
        logger.error(f"Error: Configuration file '{CONFIG_FILE}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file '{CONFIG_FILE}': {e}")
        sys.exit(1)


def execute_action(watchdog_config):
    """Executes the defined action (Bash or MQTT) when the timeout is reached."""
    wd_name = watchdog_config.get("name", watchdog_config["topic"])
    logger.error(
        "---------------------------------------------------------------------"
    )
    logger.error(f"!!! WATCHDOG ALARM for '{wd_name}' ({watchdog_config['topic']}) !!!")
    logger.error(f"No message received for {watchdog_config['interval']} seconds.")
    logger.error(
        "---------------------------------------------------------------------"
    )

    # 1. Execute Bash Command (if defined)
    if watchdog_config.get("action_cmd"):
        cmd = watchdog_config["action_cmd"]
        logger.info(f" -> Executing Bash command: {cmd}")
        try:
            # check=True ensures that an error is raised if the command fails
            subprocess.run(
                cmd,
                shell=True,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info(" -> Bash command executed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(
                f" -> ERROR in Bash command for '{wd_name}': {e.stderr.strip()}"
            )
        except FileNotFoundError:
            logger.error(
                f" -> ERROR: Bash command for '{wd_name}' not found or invalid."
            )

    # 2. Send MQTT message (if topic and payload are defined)
    if watchdog_config.get("action_mqtt_topic") and watchdog_config.get(
        "action_mqtt_payload"
    ):
        topic = watchdog_config["action_mqtt_topic"]
        payload = watchdog_config["action_mqtt_payload"]

        # Ensure that payload is sent as string/bytes
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        logger.info(f" -> Sending MQTT alarm to topic '{topic}' (Payload: {payload})")
        CLIENT.publish(topic, payload, qos=1, retain=False)
        logger.info(" -> MQTT message sent.")

    # Restart the timer immediately to continue monitoring
    setup_watchdog(watchdog_config)
    logger.info(f" -> Watchdog '{wd_name}' neu initialisiert und läuft.")


def setup_watchdog(watchdog_config):
    """Initializes or resets the timer for a specific watchdog."""
    topic = watchdog_config["topic"]

    # Cancel existing timer if it's running
    if topic in WATCHDOGS and WATCHDOGS[topic].is_alive():
        WATCHDOGS[topic].cancel()

    # Start new timer
    timer = threading.Timer(
        watchdog_config["interval"], execute_action, args=[watchdog_config]
    )
    WATCHDOGS[topic] = timer
    timer.start()


# --- MQTT Callbacks ---


def on_connect(client, userdata, flags, reasonCode, properties):
    """Called when the client connects to the broker (API v2 signature)."""
    if reasonCode == 0:
        logger.info("Successfully connected to MQTT broker.")

        # Subscribe to all topics and start timers
        for wd_config in CONFIG["watchdogs"]:
            topic = wd_config["topic"]
            client.subscribe(topic)
            setup_watchdog(wd_config)
            logger.info(
                f"Watchdog '{wd_config.get('name', topic)}': Subscribed to topic '{topic}', timer started ({wd_config['interval']}s)."
            )
    else:
        logger.error(f"Connection error. Code: {reasonCode}")
        sys.exit(1)


def on_message(client, userdata, msg):
    """Called when a message is received on a subscribed topic."""
    topic = msg.topic

    # Find the watchdog configuration for this topic
    wd_config = next((wd for wd in CONFIG["watchdogs"] if wd["topic"] == topic), None)

    if wd_config:
        # Message received -> reset timer
        setup_watchdog(wd_config)
        wd_name = wd_config.get("name", topic)
        logger.debug(f"Message received on '{wd_name}' ({topic}). Timer reset.")


# --- Main Program ---

if __name__ == "__main__":
    load_config()

    mqtt_config = CONFIG["mqtt"]

    # Initialize Paho-Client with latest Callback API version
    CLIENT = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    # Set authentication
    if mqtt_config.get("username") and mqtt_config.get("password"):
        CLIENT.username_pw_set(mqtt_config["username"], mqtt_config["password"])

    CLIENT.on_connect = on_connect
    CLIENT.on_message = on_message

    # Establish connection
    try:
        CLIENT.connect(
            host=mqtt_config["broker"], port=mqtt_config["port"], keepalive=60
        )
    except Exception as e:
        logger.error(f"Could not connect to MQTT broker: {e}")
        sys.exit(1)

    logger.info("--- MQTT Watchdog started ---")
    try:
        CLIENT.loop_forever()
    except KeyboardInterrupt:
        logger.info("Script terminated by user (KeyboardInterrupt).")
    finally:
        # Stop all timers on exit
        for timer in WATCHDOGS.values():
            timer.cancel()
        if CLIENT:
            CLIENT.disconnect()
        logger.info("All resources released. Watchdog terminated.")
