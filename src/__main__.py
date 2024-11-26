import threading
import importlib
import signal
import sys

from modules.logger import Logger
from modules.utils import get_config

CONFIG_PATH = '/etc/icebox/config.json'
MODULES = ['icepick', 'icicle', 'snowdog']

shutdown_flag = threading.Event()

def signal_handler(signum, frame):
    global shutdown_flag
    shutdown_flag.set()

def start_ice_cube_thread(ice_cube_name, config_path):
    ice_cube = importlib.import_module(ice_cube_name)
    ice_cube_class = getattr(ice_cube, ice_cube_name.capitalize())
    instance = ice_cube_class(config_path)
    thread = threading.Thread(target=instance.run)
    thread.start()
    return thread

def main():
    global shutdown_flag
    signal.signal(signal.SIGTERM, signal_handler)

    config = get_config(CONFIG_PATH)
    Logger.configure(
        log_file=config['log']['file'],
        log_level=config['log']['level']
    )

    logger = Logger.get_logger('main')
    logger.info("Icebox starting...")

    threads = []
    for ice_cube_name in MODULES:
        try:
            thread = start_ice_cube_thread(ice_cube_name, CONFIG_PATH)
            threads.append(thread)
        except Exception as e:
            logger.error(f"Failed to start thread for ice cube {ice_cube_name}: {e}")
            sys.exit(1)

    try:
        while not shutdown_flag.is_set():
            for thread in threads:
                thread.join(1)
        for thread in threads:
            thread.stop()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

    logger.info("Waiting for threads to finish...")
    for thread in threads:
        thread.join()

    logger.info("Icebox stopped")

if __name__ == "__main__":
    main()
