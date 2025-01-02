import threading
import queue
import time
import os
from typing import Callable


class LogWatcher:
    def __init__(
        self,
        file_path: str,
        tag: str,
        message_handler: Callable[[str], None]
    ) -> None:
        self.file_path = file_path
        self.tag = tag
        self.message_handler = message_handler
        self.message_queue = queue.Queue()
        self.shutdown_flag = threading.Event()
        self.threads = []

    def start(self) -> None:
        log_watcher_thread = threading.Thread(target=self.watch_log_file)
        message_worker_thread = threading.Thread(target=self.process_messages)

        self.threads.extend([log_watcher_thread, message_worker_thread])

        for thread in self.threads:
            thread.daemon = True
            thread.start()

    def stop(self) -> None:
        self.shutdown_flag.set()
        self.message_queue.put(None)
        for thread in self.threads:
            thread.join()

    def watch_log_file(self) -> None:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Log file not found: {self.file_path}")

        with open(self.file_path, 'r') as file:
            file.seek(0, 2)

            while not self.shutdown_flag.is_set():
                line = file.readline()
                if not line:
                    time.sleep(1)
                    continue

                if self.tag in line:
                    self.message_queue.put(line.strip())

    def process_messages(self) -> None:
        while not self.shutdown_flag.is_set():
            try:
                message = self.message_queue.get(timeout=1)
                if message is None:
                    break
                if message:
                    self.message_handler(message)
                self.message_queue.task_done()
            except queue.Empty:
                continue
