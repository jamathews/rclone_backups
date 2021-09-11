#!/usr/bin/env python3.9
"""
Perform backups using rclone
"""

import argparse
import logging
import os
import pprint
import sys
from datetime import datetime

from backup_tracker import BackupTracker
from restore_tracker import RestoreTracker


def verbosity_to_log_level(verbosity=2):
    if verbosity <= 0:
        return logging.CRITICAL
    if verbosity == 1:
        return logging.ERROR
    if verbosity == 2:
        return logging.WARNING
    if verbosity == 3:
        return logging.INFO
    if verbosity >= 4:
        return logging.DEBUG


class UndefinedAction(Exception):
    pass


def logging_setup(args):
    log_level = verbosity_to_log_level(args.verbose)
    log_formatter = logging.Formatter(fmt='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger()
    root_logger.setLevel(level=log_level)

    os.makedirs(args.logdir, exist_ok=True)
    file_handler = logging.FileHandler(filename=os.path.join(args.logdir, f"{datetime.utcnow().isoformat()}.log"))
    file_handler.setFormatter(fmt=log_formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt=log_formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)


def command_line():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.title = "Action"
    action.add_argument("--backup",
                        help="Perform a backup",
                        action="store_true",
                        )
    action.add_argument("--restore",
                        help="Perform a restore",
                        action="store_true",
                        )
    parser.add_argument("-t", "--tracker",
                        help="progress tracking file to support resuming after interruption",
                        type=str,
                        default="rclone_tracker.db.sqlite3",
                        )
    parser.add_argument("-d", "--destination",
                        help="For backups: the name given to the B2 bucket where backups will be stored. "
                             "For restores: the path where restored files will be saved.",
                        type=str,
                        default="",
                        )
    parser.add_argument("-v", "--verbose",
                        help="verbosity of logging, -v is minimal, -vvvv is very verbose",
                        action='count',
                        default=0
                        )
    parser.add_argument("-l", "--logdir",
                        help="Directory in which to dump completed logs",
                        type=str,
                        default=os.path.join(os.getcwd(), "logs"),
                        )
    parser.add_argument("-r", "--remote-name",
                        help="The name given to the B2 destination remote in your rclone config",
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
    args = parser.parse_args()
    return args


def main():
    args = command_line()
    logging_setup(args)
    logging.debug(pprint.pformat(sys.argv))

    if args.backup:
        tracker_class = BackupTracker
    elif args.restore:
        tracker_class = RestoreTracker
    else:
        raise UndefinedAction
    tracker = tracker_class(filename=args.tracker,
                            sources=args.sources,
                            remote_name=args.remote_name,
                            destination=args.destination,
                            logdir=args.logdir,
                            verbosity=(args.verbose - 2),
                            )
    tracker.resume()


if __name__ == '__main__':
    main()
