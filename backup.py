#!/usr/bin/env python3.9
"""
Perform backups using rclone
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
from datetime import datetime

verbosity_to_log_level = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.WARNING,
    3: logging.INFO,
    4: logging.DEBUG,
}


class BackupTracker:
    _interrupt_requested = False

    def __init__(self, filename, sources, remote_name, bucket_name, logdir) -> None:
        self._filename = filename
        self._top_level_sources = sources
        self._remote_name = remote_name
        self._bucket_name = bucket_name
        self._logdir = logdir
        self._detailed_sources = []
        self._tracker = {}

        signal.signal(signal.SIGINT, BackupTracker._sigint_handler)
        if os.path.isfile(self.filename):
            logging.debug(f"{self.filename} exists, we'll use that for backups")
            self._load_from_disk()
        else:
            logging.debug(f"{self.filename} doesn't exist, generating from {self.top_level_sources}")
            self.make_fresh_tracker()
            self._save_to_disk()
        if self._interrupt_requested:
            sys.exit(1)

    @property
    def filename(self):
        return self._filename

    @property
    def top_level_sources(self):
        return self._top_level_sources

    @property
    def remote_name(self):
        return self._remote_name

    @property
    def bucket_name(self):
        return self._bucket_name

    @property
    def logdir(self):
        os.makedirs(self._logdir, exist_ok=True)
        return self._logdir

    @property
    def hostname(self):
        return socket.gethostname()

    @property
    def dest_prefix(self):
        return f"{self.remote_name}:{self.bucket_name}/{self.hostname}"

    @staticmethod
    def _sigint_handler(sig, frame):
        BackupTracker._interrupt_requested = True

    def _populate_sources_from_disk(self):
        for source in self.top_level_sources:
            for root, dirs, _ in os.walk(source, topdown=False, followlinks=False):
                for subdir in dirs:
                    self._detailed_sources.append(os.path.join(root, subdir))
            self._detailed_sources.append(source)

    def make_fresh_tracker(self):
        self._populate_sources_from_disk()
        tracker_sources = {str(index): {"path": source} for index, source in enumerate(self._detailed_sources)}
        self._tracker = {
            "next": 0,
            "sources": tracker_sources
        }

    def _load_from_disk(self):
        with open(self.filename, "r") as tracker_file:
            self._tracker = json.load(tracker_file)

    def _save_to_disk(self):
        with open(self.filename, "w") as tracker_file:
            json.dump(self._tracker, tracker_file, indent=2)

    def resume_backups(self):
        next_source = self._tracker["next"]
        sources = self._tracker["sources"]
        while not self._interrupt_requested and (source := sources.get(str(next_source))):
            backup_command = [
                'rclone',
                'copy',
                source["path"],
                f'{self.dest_prefix}{source["path"]}',
            ]
            logging.info(" ".join(backup_command))
            try:
                subprocess.run(backup_command, capture_output=True, check=True, encoding="ascii")
                next_source += 1
                self._tracker["next"] = next_source
                source["done"] = datetime.utcnow().isoformat()
                self._save_to_disk()
            except subprocess.CalledProcessError as exception:
                error_message = f"\n" \
                                f"{exception.returncode=}\n" \
                                f"{exception.cmd=}\n" \
                                f"{exception.output=}\n" \
                                f"{exception.stdout=}\n" \
                                f"{exception.stderr=}\n"
                logging.error(error_message)
                break
        logging.info("done")
        os.rename(self.filename, os.path.join(self.logdir, f"{datetime.utcnow().isoformat()}-{os.path.basename(self.filename)}"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tracker",
                        help="progress tracking file to support resuming after interruption",
                        type=str,
                        default="backup_tracker.json",
                        )
    parser.add_argument("-r", "--remote-name",
                        help="The name given to the B2 destination remote in your rclone config",
                        type=str,
                        required=True,
                        )
    parser.add_argument("-b", "--bucket-name",
                        help="The name given to the B2 bucket where backups will be stored",
                        type=str,
                        required=True,
                        )
    parser.add_argument("-s", "--sources",
                        help="absolute path[s] to be backed up",
                        type=str,
                        nargs="+",
                        default=[os.getcwd()],
                        required=True,
                        )
    parser.add_argument("-v", "--verbose",
                        help="verbosity of logging, -v is minimal, -vvvv is verbose",
                        action='count',
                        default=0
                        )
    parser.add_argument("-l", "--logdir",
                        help="Directory in which to dump completed logs",
                        type=str,
                        default=os.path.join(os.getcwd(), "logs"),
                        )
    args = parser.parse_args()
    logging.basicConfig(level=verbosity_to_log_level.get(args.verbose, 2), format='%(asctime)s: %(levelname)s:\t%(message)s')

    tracker_filename = args.tracker
    tracker = BackupTracker(tracker_filename, args.sources, args.remote_name, args.bucket_name, args.logdir)
    tracker.resume_backups()


if __name__ == '__main__':
    main()
