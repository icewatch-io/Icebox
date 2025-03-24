import threading
import importlib
import signal
import sys
import json
from pathlib import Path

from modules.logger import Logger
from modules.config_store import ConfigStore
from icewatch import IcewatchClient
from modules.alerter import Alerter

CONFIG_PATH = '/etc/icebox/config.json'
ICEWATCH_CONFIG_PATH = '/etc/icebox/icewatch.json'
MODULES = ['icepick', 'icicle', 'snowdog']

shutdown_flag = threading.Event()
instances = []


def signal_handler(signum: int, frame: any) -> None:
    global shutdown_flag
    shutdown_flag.set()


def start_ice_cube_thread(ice_cube_name: str) -> tuple:
    logger = Logger.get_logger('startup')
    logger.debug(f"Starting {ice_cube_name}")
    ice_cube = importlib.import_module(ice_cube_name)
    ice_cube_class = getattr(ice_cube, ice_cube_name.capitalize())
    instance = ice_cube_class()
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    logger.debug(f"Started {ice_cube_name} thread")
    return thread, instance


def init_config() -> None:
    """Initialize configuration."""
    logger = Logger.get_logger('main')
    config_store = ConfigStore()

    if Path(ICEWATCH_CONFIG_PATH).exists():
        logger.info("Icewatch config found, initializing Icewatch")
        try:
            with open(ICEWATCH_CONFIG_PATH) as f:
                icewatch_config = json.load(f)

            icewatch = IcewatchClient(
                api_url=icewatch_config['api_url'],
                device_id=icewatch_config['device_id'],
                api_key=icewatch_config['api_key'],
                config_path=icewatch_config['config_path']
            )

            alerter = Alerter()
            alerter.configure_icewatch({})

            icewatch_thread = threading.Thread(
                target=icewatch.run,
                daemon=True
            )
            icewatch_thread.start()

            if not icewatch.wait_for_initial_config():
                logger.warning("Failed to get config from Icewatch, trying cached config")
                if not icewatch._load_cached_config():
                    logger.warning("No cached config found, falling back to local config")
                    config_store.load_config(CONFIG_PATH)

        except Exception as e:
            logger.error(f"Failed to initialize Icewatch: {e}")
            logger.info("Falling back to local config")
            config_store.load_config(CONFIG_PATH)
    else:
        logger.info("No Icewatch config found, using local config")
        config_store.load_config(CONFIG_PATH)


def main() -> None:
    # Set up signal handlers first in main thread
    global shutdown_flag, instances
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    Logger.configure(
        log_file='/var/log/icebox/icebox.log',
        log_level='DEBUG',
    )
    logger = Logger.get_logger('main')
    logger.info("Icebox starting...")

    init_config()
    config_store = ConfigStore(shutdown_flag=shutdown_flag)

    Logger.configure(
        log_file=config_store.get('log.file'),
        log_level=config_store.get('log.level')
    )

    threads = []
    for ice_cube_name in MODULES:
        try:
            thread, instance = start_ice_cube_thread(ice_cube_name)
            threads.append(thread)
            instances.append(instance)
        except Exception as e:
            logger.error(f"Failed to start thread for ice cube {ice_cube_name}: {e}")
            sys.exit(1)

    try:
        while True:
            if shutdown_flag.is_set():
                break
            shutdown_flag.wait(1.0)
    except KeyboardInterrupt:
        shutdown_flag.set()

    logger.info("Shutting down...")

    for instance in instances:
        try:
            instance.stop()
        except Exception as e:
            logger.error(f"Error stopping instance: {e}")

    logger.info("Waiting for threads to finish...")
    for thread in threads:
        try:
            thread.join(timeout=5.0)
        except Exception as e:
            logger.error(f"Error joining thread: {e}")

    logger.info("Icebox stopped")


if __name__ == "__main__":
    main()
