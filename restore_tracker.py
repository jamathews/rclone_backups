import json
import logging
import subprocess

from base_tracker import BaseTracker


class RestoreTracker(BaseTracker):

    @property
    def dest_prefix(self):
        return f"{self.destination}"

    @property
    def source_prefix(self):
        return f"{self.remote_name}:"

    def populate_source(self, source):
        if not source[-1] == "/":
            source += "/"
        
        # If depth is 0, we just want to rclone the top-level directory itself.
        if self._depth is not None and self._depth < 0:
            return [source]

        get_remote_contents = [
            "rclone",
            "lsjson",
            "--dirs-only",
            f"{self.remote_name}:{source}",
        ]
        if self._depth is None or self._depth > 0:
             get_remote_contents.append("--recursive")
        
        # Note: rclone lsjson doesn't have a built-in max-depth like find,
        # but we can filter it if we needed to be precise.
        # For now, we'll just toggle between recursive and non-recursive.

        try:
            logging.debug(" ".join(get_remote_contents))
            rclone_proc = subprocess.run(get_remote_contents, capture_output=True, check=True, encoding="ascii")
            remote_content = json.loads(rclone_proc.stdout)
            logging.debug(remote_content)
            
            remote_sources = []
            for entry in remote_content:
                if entry["IsDir"]:
                    path = source + entry["Path"]
                    # If we have a depth, filter out items that are too deep
                    if self._depth is not None:
                        # Count slashes relative to the source
                        rel_path = entry["Path"]
                        depth = rel_path.strip("/").count("/") if rel_path.strip("/") else 0
                        if depth < self._depth:
                            remote_sources.append(path)
                    else:
                        remote_sources.append(path)

            if remote_sources:
                remote_sources.append(source)
            else:
                remote_sources = [source]
            remote_sources.sort(reverse=True, key=lambda x: x.count("/"))
            return remote_sources
        except subprocess.CalledProcessError as exception:
            error_message = f"\n" \
                            f"{exception.returncode=}\n" \
                            f"{exception.cmd=}\n" \
                            f"{exception.output=}\n" \
                            f"{exception.stdout=}\n" \
                            f"{exception.stderr=}\n"
            logging.error(error_message)
            raise exception
