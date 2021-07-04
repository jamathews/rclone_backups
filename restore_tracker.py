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
        get_remote_contents = [
            "rclone",
            "lsjson",
            "--recursive",
            f"{self.remote_name}:{source}",
        ]
        try:
            logging.debug(" ".join(get_remote_contents))
            rclone_proc = subprocess.run(get_remote_contents, capture_output=True, check=True, encoding="ascii")
            remote_content = json.loads(rclone_proc.stdout)
            logging.debug(remote_content)
            remote_sources = [source + entry["Path"] for entry in remote_content if entry["IsDir"]]
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
