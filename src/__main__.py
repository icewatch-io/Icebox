import threading
import importlib

from modules.logger import Logger
from modules.utils import get_config

CONFIG_PATH = '/etc/icebox/config.json'
MODULES = ['icepick', 'icicle', 'snowdog']


def start_module_thread(module_name, config_path):
    module = importlib.import_module(module_name)
    class_name = module_name.capitalize()
    module_class = getattr(module, class_name)
    instance = module_class(config_path)
    thread = threading.Thread(target=instance.run)
    thread.start()
    return thread


def main():
    config = get_config(CONFIG_PATH)
    Logger.configure(
        log_file=config['log']['file'],
        log_level=config['log']['level']
    )

    threads = []

    for module_name in MODULES:
        thread = start_module_thread(module_name, CONFIG_PATH)
        threads.append(thread)

    try:
        while True:
            for thread in threads:
                thread.join(1)
    except KeyboardInterrupt:
        print("Shutting down...")

    for thread in threads:
        thread.join()


if __name__ == '__main__':
    main()
