import argparse
import json
import os
import copy
from sqlitedict import SqliteDict


class JSON2Sqlite:
    def __init__(self, json_file):
        self.json = None
        self.json_file = json_file
        self.db = None
        self.db_file = os.path.splitext(json_file)[0] + ".sqlite"

    def __enter__(self):
        with open(self.json_file, "r") as json_file:
            self.json = json.load(json_file)
        self.db = SqliteDict(self.db_file)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.db.close()

    def convert(self):
        for key, value in self.json.items():
            self.db[key] = copy.deepcopy(value)
        self.db.commit()


def command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tracker",
                        help="progress tracking json file to be converted into a sqlite database",
                        type=str,
                        default="rclone_tracker.json",
                        )
    args = parser.parse_args()
    return args


def main():
    args = command_line()
    with JSON2Sqlite(json_file=args.tracker) as convertor:
        convertor.convert()


if __name__ == '__main__':
    main()
