import logging
import os
import signal
import sqlite3
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from datetime import datetime
from time import sleep


class BaseTracker(metaclass=ABCMeta):
    _interrupt_requested = False

    def __init__(self, filename, sources, remote_name, destination, logdir, verbosity=0, retry=False) -> None:
        self._filename = filename
        self._top_level_sources = sources
        self._remote_name = remote_name
        self._destination = destination
        self._logdir = logdir
        self._verbosity = verbosity
        self._tracker = None
        self._retry = retry
        self._sleep_on_cap_exceeded = 300

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

    @property
    def sleep_on_cap_exceeded(self):
        seconds = self._sleep_on_cap_exceeded
        self._sleep_on_cap_exceeded *= 2
        return seconds

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

    def _archive(self):
        os.makedirs(self._logdir, exist_ok=True)
        completed_db = os.path.join(self._logdir, f"{datetime.utcnow().isoformat()}-{os.path.basename(self._filename)}")
        os.rename(self._filename, completed_db)
        logging.info("Completed db saved as %s", completed_db)

    def _init_tracker(self):
        if os.path.isfile(self._filename):
            logging.debug("%s exists, we'll use that for tracking progress", self._filename)
            self._load_from_disk()
        else:
            logging.debug("%s doesn't exist, generating: %s", self._filename, str(self._top_level_sources))
            self._make_fresh_tracker()
        if self._retry:
            self.update_tracker_value("next", self.get_next_source_id(-1))

    def _load_from_disk(self):
        self._tracker = sqlite3.connect(database=self._filename)

    def _make_fresh_tracker(self):
        # TODO: do the table creation first, then _populate_sources() can be a separate thread, and resume() can start right away
        detailed_sources = map(lambda x: x.encode("utf-8", errors="backslashreplace"), self._populate_sources())

        self._tracker = sqlite3.connect(database=self._filename)
        try:
            with self._tracker:
                self._tracker.execute("""
                    CREATE TABLE tracker ( 
                        key                  text NOT NULL  PRIMARY KEY  ,
                        value                bigint     
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
                        stderr               text     ,
                        failure              text     
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
        # TODO: make a thread-safe queue of source_paths, and a bunch of workers to process them async
        source_id = self.get_tracker_value("next")

        while (source := self.get_source_path(source_id)) and not self._interrupt_requested:
            source_path = source[0].decode("utf-8", errors="backslashreplace")
            logging.info(source_path)
            rclone_command = [
                'rclone',
                'copy',
                f'{self.source_prefix}{source_path}',
                f'{self.dest_prefix}{source_path}',
            ]
            if self._verbosity >= 1:
                rclone_command.append(f"-{'v' * self._verbosity}")
            logging.debug(" ".join(rclone_command))
            result = {
                "id": source_id,
                "done": None,
                "args": None,
                "command_line": None,
                "returncode": None,
                "stdout": None,
                "stderr": None,
                "failure": None,
            }
            try:
                rclone = subprocess.run(rclone_command, capture_output=True, check=True)
                logging.debug("stdout:\n" + self._bytes_to_str(rclone.stdout))
                logging.debug("stderr:\n" + self._bytes_to_str(rclone.stderr))
                result["done"] = datetime.utcnow().isoformat()
                if self._verbosity >= 2:
                    result["args"] = str(rclone.args)
                    result["command_line"] = " ".join(["'" + arg + "'" for arg in rclone.args])
                    result["returncode"] = rclone.returncode
                    result["stdout"] = self._bytes_to_str(rclone.stdout)
                    result["stderr"] = self._bytes_to_str(rclone.stderr)
            except subprocess.CalledProcessError as exception:
                error_message = f"\n" \
                                f"{exception.returncode=}\n" \
                                f"{exception.cmd=}\n" \
                                f"{exception.output=}\n" \
                                f"{exception.stdout=}\n" \
                                f"{exception.stderr=}\n"
                logging.exception(error_message)
                if b"transaction_cap_exceeded" in exception.stderr:
                    sleep_seconds = self.sleep_on_cap_exceeded
                    error_message = f"\n" \
                                    f"Transaction Cap Exceeded. " \
                                    f"Sleeping {sleep_seconds} seconds.\n"
                    logging.exception(error_message)
                    sleep(sleep_seconds)
                result["failure"] = self._bytes_to_str(exception.stderr)
            finally:
                next_source_id = self.get_next_source_id(source_id)
                if next_source_id is not None:
                    source_id = next_source_id
                else:
                    source_id += 1
                self.update_tracker_value("next", source_id)
                self.update_source(result)
        else:
            if (failure_count := self.get_failure_count()) == 0 and not source:
                logging.info("Done rcloning %s", str(self._top_level_sources))
                self._archive()
            else:
                failures = self.get_failures()
                logging.error("Failures: %d\n\n%s",
                              failure_count,
                              failures,
                              )

    def get_source_path(self, id):
        return self._tracker.execute("""
            SELECT path
            FROM sources
            WHERE id = :id;
        """, {"id": id}).fetchone()

    def get_tracker_value(self, key_name):
        try:
            key_record = self._tracker.execute("""
                SELECT value
                FROM tracker
                WHERE key = :key_name;
            """, {"key_name": key_name}).fetchone()
            if key_record is None:
                logging.critical("No record for key = %s", key_name)
                raise RuntimeError(f"Data error: '{key_name}' should always return exactly 1 record")
        except sqlite3.Error as exception:
            logging.exception(exception)
            raise RuntimeError(f"Unable to determine '{key_name}' source")
        return key_record[0]

    def update_tracker_value(self, key_name, value):
        try:
            with self._tracker:
                self._tracker.execute("""
                    UPDATE tracker 
                    SET value = :value 
                    WHERE key = :key_name;
                """, {"key_name": key_name, "value": value})
        except sqlite3.Error as exception:
            logging.exception(exception)
            raise RuntimeError(f"Unable to update '{key_name}'")

    def update_source(self, values):
        try:
            with self._tracker:
                self._tracker.execute("""
                    UPDATE sources
                    SET
                        done = :done, 
                        args = :args, 
                        command_line = :command_line, 
                        returncode = :returncode, 
                        stdout = :stdout, 
                        stderr = :stderr, 
                        failure = :failure
                    WHERE id = :id;
                """, values)
        except sqlite3.Error as exception:
            logging.exception(exception)
            raise RuntimeError(f"Unable to update source with id={values['id']}")

    def get_failures(self):
        return self._tracker.execute("""
            SELECT * 
            FROM sources 
            WHERE failure IS NOT NULL;
        """, {"id": id}).fetchall()

    def get_next_source_id(self, id):
        return self._tracker.execute("""
            SELECT min(id)
            FROM sources
            WHERE id > :id
            AND done IS NULL;
        """, {"id": id}).fetchone()[0]

    def get_failure_count(self):
        return self._tracker.execute("""
            SELECT count(id)
            FROM sources
            WHERE failure IS NOT NULL;
        """).fetchone()[0]
