import threading
import importlib
import signal
import sys
from pathlib import Path

from modules.logger import Logger
from modules.utils import get_config
from icewatch import IcewatchClient
from modules.config_store import ConfigStore

ICEBOX_CONFIG_PATH = '/etc/icebox/config.json'
ICEWATCH_CONFIG_PATH = '/etc/icebox/icewatch.json'
MODULES = ['icepick', 'icicle', 'snowdog']

shutdown_flag = threading.Event()
instances = []


def signal_handler(signum: int, frame: any) -> None:
    global shutdown_flag
    shutdown_flag.set()


def start_ice_cube_thread(ice_cube_name: str) -> tuple:
    config_store = ConfigStore()
    if not config_store.get_config():
        config_store.load_config(config_path)
    ice_cube = importlib.import_module(ice_cube_name)
    ice_cube_class = getattr(ice_cube, ice_cube_name.capitalize())
    instance = ice_cube_class(config_path)
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    return thread, instance


def main() -> None:
    global shutdown_flag, instances

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    Logger.configure(
        log_file="/var/log/icebox/icebox.log",
        log_level="INFO"
    )
    logger = Logger.get_logger('startup')

    config_store = ConfigStore()
    config = config_store.get_config()
    if not config:
        config_store.load_config(ICEBOX_CONFIG_PATH)
        config = config_store.get_config()

    if Path(ICEWATCH_CONFIG_PATH).exists():
        logger.info("Icewatch config found")
        try:
            icewatch_config = get_config(ICEWATCH_CONFIG_PATH)
            icewatch = IcewatchClient(
                api_url=icewatch_config['api_url'],
                device_id=icewatch_config['device_id'],
                api_key=icewatch_config['api_key'],
                config_path=icewatch_config['config_path']
            )

            logger.info(f"Checking into icewatch as {icewatch_config['device_id']}")
            if icewatch.check_in():
                logger.info(f"Check in succeeded")
                updated_config = get_config(icewatch_config['config_path'])
                if updated_config:
                    config = updated_config
        except Exception as e:
            logger.error(f"Failed to initialize Icewatch: {str(e)}")
            sys.exit(1)

    Logger.configure(
        log_file=config['log']['file'],
        log_level=config['log']['level']
    )

    logger = Logger.get_logger('main')
    logger.info("Icebox starting...")

    threads = []
    for ice_cube_name in MODULES:
        try:
            thread, instance = start_ice_cube_thread(
                ice_cube_name,
                ICEBOX_CONFIG_PATH
            )
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

    # Stop all instances
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
