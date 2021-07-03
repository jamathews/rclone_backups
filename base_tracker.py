import json
import logging
import os
import signal
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from datetime import datetime


class BaseTracker(metaclass=ABCMeta):
    _interrupt_requested = False

    def __init__(self, filename, sources, remote_name, destination, logdir) -> None:
        self._filename = filename
        self._top_level_sources = sources
        self._remote_name = remote_name
        self._destination = destination
        self._logdir = logdir
        self._tracker = {
            "next": 0,
            "sources": {},
        }

        signal.signal(signal.SIGINT, BaseTracker._sigint_handler)
        if os.path.isfile(self.filename):
            logging.debug("%s exists, we'll use that for tracking progress", self.filename)
            self.load_from_disk()
        else:
            logging.debug("%s doesn't exist, generating: %s", self.filename, str(self.top_level_sources))
            self.make_fresh_tracker()
            self.save_to_disk()
        if self._interrupt_requested:
            sys.exit(1)

    @property
    @abstractmethod
    def dest_prefix(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def source_prefix(self):
        raise NotImplementedError

    @abstractmethod
    def populate_source(self, source):
        raise NotImplementedError

    @staticmethod
    def _sigint_handler(sig, _):
        logging.debug("received signal %s", signal.Signals(sig).name)
        BaseTracker._interrupt_requested = True

    @property
    def destination(self):
        if not self._destination[-1] == "/":
            self._destination += "/"
        return self._destination

    @property
    def filename(self):
        return self._filename

    @property
    def interrupt_requested(self):
        return self._interrupt_requested

    @property
    def logdir(self):
        os.makedirs(self._logdir, exist_ok=True)
        return self._logdir

    @property
    def remote_name(self):
        return self._remote_name

    @property
    def top_level_sources(self):
        return self._top_level_sources

    @property
    def tracker(self):
        return self._tracker

    def archive_log(self):
        completed_log = os.path.join(self.logdir, f"{datetime.utcnow().isoformat()}-{os.path.basename(self.filename)}")
        os.rename(self.filename, completed_log)
        logging.info("Log saved as %s", completed_log)

    def load_from_disk(self):
        with open(self.filename, "r") as tracker_file:
            self._tracker = json.load(tracker_file)

    def make_fresh_tracker(self):
        detailed_sources = self.populate_sources()
        tracker_sources = {
            str(index): {"path": source} for index, source in enumerate(detailed_sources)
        }
        self.tracker["next"] = 0
        self.tracker["sources"] = tracker_sources

    def populate_sources(self):
        detailed_sources = []
        for source in self.top_level_sources:
            detailed_sources.extend(self.populate_source(source))
        return detailed_sources

    def resume(self):
        next_source = self.tracker["next"]
        sources = self.tracker["sources"]
        while not self.interrupt_requested and (source := sources.get(str(next_source))):
            rclone_command = [
                'rclone',
                'copy',
                f'{self.source_prefix}{source["path"]}',
                f'{self.dest_prefix}{source["path"]}',
            ]
            logging.info(" ".join(rclone_command))
            try:
                subprocess.run(rclone_command, capture_output=True, check=True, encoding="ascii")
                next_source += 1
                self.tracker["next"] = next_source
                source["done"] = datetime.utcnow().isoformat()
                self.save_to_disk()
            except subprocess.CalledProcessError as exception:
                error_message = f"\n" \
                                f"{exception.returncode=}\n" \
                                f"{exception.cmd=}\n" \
                                f"{exception.output=}\n" \
                                f"{exception.stdout=}\n" \
                                f"{exception.stderr=}\n"
                logging.error(error_message)
                break
        else:
            logging.info("Done rcloning %s", str(self.top_level_sources))
            self.archive_log()

    def save_to_disk(self):
        with open(self.filename, "w") as tracker_file:
            json.dump(self._tracker, tracker_file, indent=2)
