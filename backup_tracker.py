import os
import socket

from base_tracker import BaseTracker


class BackupTracker(BaseTracker):

    @property
    def dest_prefix(self):
        return f"{self.remote_name}:{self.destination}{socket.gethostname()}"

    @property
    def source_prefix(self):
        return f""

    def populate_source(self, source):
        detailed_sources = []
        for root, dirs, _ in os.walk(source, topdown=False, followlinks=False):
            detailed_sources.extend([os.path.join(root, subdir) for subdir in dirs])
        detailed_sources.append(source)
        return detailed_sources
