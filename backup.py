#!/usr/bin/env python3.9
"""
Perform backups using rclone
"""

import argparse
import logging
import os

from backup_tracker import BackupTracker
from restore_tracker import RestoreTracker

verbosity_to_log_level = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.WARNING,
    3: logging.INFO,
    4: logging.DEBUG,
}


class UndefinedAction(Exception):
    pass


def main():
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
                        default="rclone_tracker.json",
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
    logging.basicConfig(
        level=verbosity_to_log_level.get(args.verbose, 2),
        format='%(asctime)s: %(levelname)s:\t%(message)s',
    )

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
