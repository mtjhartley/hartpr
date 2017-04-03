import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from subprocess import Popen, PIPE

class ServerRestartWatcher(FileSystemEventHandler):
    """Logs all the events captured."""

    def __init__(self):
        self.process = Popen(['python', 'main.py'])

    def restart_server(self):
        self.process.terminate()
        self.process = Popen(['python', 'main.py'])

    def on_moved(self, event):
        super(ServerRestartWatcher, self).on_moved(event)
        self.restart_server()

    def on_created(self, event):
        super(ServerRestartWatcher, self).on_created(event)
        self.restart_server()

    def on_deleted(self, event):
        super(ServerRestartWatcher, self).on_deleted(event)
        self.restart_server()

    def on_modified(self, event):
        super(ServerRestartWatcher, self).on_modified(event)
        self.restart_server()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else './'
    event_handler = ServerRestartWatcher()

    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()