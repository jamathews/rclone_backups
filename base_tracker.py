import json
import logging
import os
import signal
import sqlite3
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from datetime import datetime


class BaseTracker(metaclass=ABCMeta):
    _interrupt_requested = False

    def __init__(self, filename, sources, remote_name, destination, logdir, verbosity=0) -> None:
        self._filename = filename
        self._top_level_sources = sources
        self._remote_name = remote_name
        self._destination = destination
        self._logdir = logdir
        self._verbosity = verbosity
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

    @staticmethod
    def _bytes_to_str(message: bytes) -> str:
        if isinstance(message, str):
            return message
        encodings = ["utf-8", "ascii"]
        for encoding in encodings:
            decoded = BaseTracker._decode(message, encoding)
            if decoded:
                return decoded
        else:
            return message.hex()

    @staticmethod
    def _decode(message, encoding):
        try:
            decoded = message.decode(encoding=encoding, errors="backslashreplace")
            return decoded
        except UnicodeError:
            logging.exception("Failed to decode bytes to string.")
            return None

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

    def _load_from_disk(self):
        self._tracker = sqlite3.connect(database=self._filename)

    def _make_fresh_tracker(self):
        detailed_sources = self._populate_sources()

        self._tracker = sqlite3.connect(database=self._filename)
        try:
            with self._tracker:
                self._tracker.execute("""
                    CREATE TABLE tracker ( 
                        key                  text NOT NULL  PRIMARY KEY  ,
                        value                text     
                     );
                 """)

                self._tracker.execute("""
                    CREATE TABLE sources ( 
                        id                   bigint NOT NULL  PRIMARY KEY  ,
                        path                 text NOT NULL    ,
                        done                 timestamp     ,
                        args                 text     ,
                        command_line         text     ,
                        returncode           integer     ,
                        stdout               text     ,
                        stderr               text     
                     );
                """)

                self._tracker.execute("""
                    INSERT INTO tracker
                        ( key, value) VALUES ( ?, ? );
                """, ("next", 0))

                self._tracker.executemany("""
                    INSERT INTO sources
                        ( id, path) VALUES ( ?, ? );
                """, enumerate(detailed_sources))
        except sqlite3.Error as exception:
            logging.exception(exception)
            raise RuntimeError("Unable to make fresh tracker database")

    def _populate_sources(self):
        detailed_sources = []
        for source in self._top_level_sources:
            detailed_sources.extend(self.populate_source(source))
        return detailed_sources

    def resume(self):
        next_source = self._tracker["next"]
        sources = self._tracker["sources"]
        while (source := sources.get(str(next_source))) and not self._interrupt_requested:
            logging.info(source["path"])
            rclone_command = [
                'rclone',
                'copy',
                f'{self.source_prefix}{source["path"]}',
                f'{self.dest_prefix}{source["path"]}',
            ]
            if self._verbosity:
                rclone_command.append(f"-{'v' * self._verbosity}")
            logging.debug(" ".join(rclone_command))
            try:
                rclone = subprocess.run(rclone_command, capture_output=True, check=True)
                logging.debug("stdout:\n" + self._bytes_to_str(rclone.stdout))
                logging.debug("stderr:\n" + self._bytes_to_str(rclone.stderr))
                source["done"] = datetime.utcnow().isoformat()
                if self._verbosity >= 2:
                    source["args"] = rclone.args
                    source["command_line"] = " ".join(["'" + arg + "'" for arg in rclone.args])
                    source["returncode"] = rclone.returncode
                    source["stdout"] = self._bytes_to_str(rclone.stdout)
                    source["stderr"] = self._bytes_to_str(rclone.stderr)
            except subprocess.CalledProcessError as exception:
                error_message = f"\n" \
                                f"{exception.returncode=}\n" \
                                f"{exception.cmd=}\n" \
                                f"{exception.output=}\n" \
                                f"{exception.stdout=}\n" \
                                f"{exception.stderr=}\n"
                logging.exception(error_message)
                source["failure"] = self._bytes_to_str(exception.stderr)
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
