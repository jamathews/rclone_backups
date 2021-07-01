#!/usr/bin/env python3.9
"""
Perform backups using rclone
"""

import argparse
import json
import logging
import os
import signal
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s:\t%(message)s')


class Tracker():
    _interrupt_requested = False

    def __init__(self, filename, sources) -> None:
        self._filename = filename
        self._top_level_sources = sources
        self._detailed_sources = []
        self._tracker = {}

        signal.signal(signal.SIGINT, Tracker._sigint_handler)
        if os.path.isfile(self._filename):
            logging.debug(f"{self._filename} exists, we'll use that for backups")
            self._load_from_disk()
        else:
            logging.debug(f"{self._filename} doesn't exist, generating from {self._top_level_sources}")
            self.make_fresh_tracker()
            self._save_to_disk()
        if self._interrupt_requested:
            sys.exit(1)

    @staticmethod
    def _sigint_handler(sig, frame):
        Tracker._interrupt_requested = True

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

    @property
    def filename(self):
        return self._filename

    @property
    def top_level_sources(self):
        return self._top_level_sources

    def _load_from_disk(self):
        with open(self._filename, "r") as tracker_file:
            self._tracker = json.load(tracker_file)

    def _save_to_disk(self):
        with open(self._filename, "w") as tracker_file:
            json.dump(self._tracker, tracker_file, indent=2)

    def resume_backups(self):
        next_source = self._tracker["next"]
        sources = self._tracker["sources"]
        while not self._interrupt_requested and (source := sources.get(str(next_source))):
            logging.info("rclone " + source["path"])
            next_source += 1
            self._tracker["next"] = next_source
            self._save_to_disk()
        logging.info("done")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tracker",
                        help="progress tracking file to support resuming after interruption",
                        type=str,
                        nargs=1,
                        default="backup_tracker.json",
                        )
    parser.add_argument("-s", "--sources",
                        help="absolute path[s] to be backed up",
                        type=str,
                        nargs="+",
                        default=[os.getcwd()],
                        )
    args = parser.parse_args()
    tracker_filename = args.tracker
    tracker = Tracker(tracker_filename, args.sources)
    tracker.resume_backups()


if __name__ == '__main__':
    main()
