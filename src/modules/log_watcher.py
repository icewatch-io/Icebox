import threading
import queue
import time
import os

class LogWatcher:

    def __init__(self, file_path, tag, message_handler):
        self.file_path = file_path
        self.tag = tag
        self.message_handler = message_handler
        self.message_queue = queue.Queue()

    def start(self):
        log_watcher_thread = threading.Thread(target=self.watch_log_file)
        log_watcher_thread.start()

        message_worker_thread = threading.Thread(target=self.process_messages)
        message_worker_thread.start()

    def watch_log_file(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Log file not found: {self.file_path}")
        with open(self.file_path, 'r') as file:
            file.seek(0, 2)

            while True:
                line = file.readline()
                if not line:
                    time.sleep(1)
                    continue

                if self.tag in line:
                    self.message_queue.put(line.strip())

    def process_messages(self):
        while True:
            message = self.message_queue.get()
            if message:
                self.message_handler(message)
            self.message_queue.task_done()
