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
        if self._depth is not None and self._depth < 0:
            return [source]

        base_depth = source.rstrip(os.path.sep).count(os.path.sep)
        for root, dirs, _ in os.walk(source, topdown=True, followlinks=False):
            current_depth = root.rstrip(os.path.sep).count(os.path.sep) - base_depth

            if self._depth is not None and current_depth >= self._depth:
                # We have reached the max depth.
                # Don't recurse into subdirectories by clearing the 'dirs' list.
                # But we still want to add these subdirectories as sources.
                detailed_sources.extend([os.path.join(root, subdir) for subdir in dirs])
                del dirs[:]
            else:
                # Still below max depth, add the immediate subdirectories.
                detailed_sources.extend([os.path.join(root, subdir) for subdir in dirs])

        detailed_sources.append(source)
        # Remove duplicates and ensure the sources are unique (if any)
        return sorted(list(set(detailed_sources)), reverse=True, key=lambda x: x.count(os.path.sep))
