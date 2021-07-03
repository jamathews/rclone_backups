import os
import socket

from base_tracker import BaseTracker


class BackupTracker(BaseTracker):

    @property
    def dest_prefix(self):
        return f"{self.remote_name}:{self.bucket_name}/{self.hostname}"

    @property
    def source_prefix(self):
        return f""

    @property
    def hostname(self):
        return socket.gethostname()

    def populate_sources(self):
        detailed_sources = []
        for source in self.top_level_sources:
            for root, dirs, _ in os.walk(source, topdown=False, followlinks=False):
                for subdir in dirs:
                    detailed_sources.append(os.path.join(root, subdir))
            detailed_sources.append(source)
        return detailed_sources
