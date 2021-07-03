#!/usr/bin/env python3.9
"""
Perform backups using rclone
"""

import argparse
import logging
import os

from backup_tracker import BackupTracker

verbosity_to_log_level = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.WARNING,
    3: logging.INFO,
    4: logging.DEBUG,
}


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
                        default="",
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
    logging.basicConfig(
        level=verbosity_to_log_level.get(args.verbose, 2),
        format='%(asctime)s: %(levelname)s:\t%(message)s',
    )

    tracker_filename = args.tracker
    tracker = BackupTracker(tracker_filename, args.sources, args.remote_name, args.bucket_name, args.logdir)
    tracker.resume()


if __name__ == '__main__':
    main()
