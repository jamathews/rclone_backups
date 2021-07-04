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
        self._tracker = None

        signal.signal(signal.SIGINT, BaseTracker._sigint_handler)
        self._init_tracker()
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
        if self._destination and not self._destination[-1] == "/":
            self._destination += "/"
        return self._destination

    @property
    def remote_name(self):
        return self._remote_name

    def _archive_log(self):
        os.makedirs(self._logdir, exist_ok=True)
        completed_log = os.path.join(self._logdir, f"{datetime.utcnow().isoformat()}-{os.path.basename(self._filename)}")
        os.rename(self._filename, completed_log)
        logging.info("Log saved as %s", completed_log)

    def _init_tracker(self):
        if os.path.isfile(self._filename):
            logging.debug("%s exists, we'll use that for tracking progress", self._filename)
            self._load_from_disk()
        else:
            logging.debug("%s doesn't exist, generating: %s", self._filename, str(self._top_level_sources))
            self._make_fresh_tracker()
            self._save_to_disk()

    def _load_from_disk(self):
        with open(self._filename, "r") as tracker_file:
            self._tracker = json.load(tracker_file)

    def _make_fresh_tracker(self):
        detailed_sources = self._populate_sources()
        self._tracker = {
            "next": 0,
            "sources": {
                str(index): {"path": source} for index, source in enumerate(detailed_sources)
            },
        }

    def _populate_sources(self):
        detailed_sources = []
        for source in self._top_level_sources:
            detailed_sources.extend(self.populate_source(source))
        return detailed_sources

    def _save_to_disk(self):
        with open(self._filename, "w") as tracker_file:
            json.dump(self._tracker, tracker_file, indent=2)

    def resume(self):
        next_source = self._tracker["next"]
        sources = self._tracker["sources"]
        while (source := sources.get(str(next_source))) and not self._interrupt_requested:
            rclone_command = [
                'rclone',
                'copy',
                f'{self.source_prefix}{source["path"]}',
                f'{self.dest_prefix}{source["path"]}',
            ]
            logging.info(" ".join(rclone_command))
            try:
                subprocess.run(rclone_command, capture_output=True, check=True, encoding="ascii")
                source["done"] = datetime.utcnow().isoformat()
            except subprocess.CalledProcessError as exception:
                error_message = f"\n" \
                                f"{exception.returncode=}\n" \
                                f"{exception.cmd=}\n" \
                                f"{exception.output=}\n" \
                                f"{exception.stdout=}\n" \
                                f"{exception.stderr=}\n"
                logging.error(error_message)
                source["failure"] = exception.stderr
                self._tracker["failure_count"] = self._tracker.get("failure_count", 0) + 1
            finally:
                next_source += 1
                self._tracker["next"] = next_source
                self._save_to_disk()
        else:
            if not source and self._tracker.get("failure_count", 0) == 0:
                logging.info("Done rcloning %s", str(self._top_level_sources))
                self._archive_log()
            else:
                failures = [source for _, source in self._tracker["sources"].items() if source.get("failure") is not None]
                logging.error("Failures: %d\n\n%s",
                              self._tracker.get("failure_count", 0),
                              json.dumps(failures, indent=2),
                              )
