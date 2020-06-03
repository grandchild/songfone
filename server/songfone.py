import os
import sys

from config import config, Config
from database import update_database
from wants import fulfill_wants


def main(config_file=None):
    config.load(config_file or "songfone.conf")
    config.make_output()
    wants_changed_time = os.path.getmtime(config.wants_file)
    fulfill_wants()
    print(":: wanted files complete")
    update_database()
    print(":: database update complete")
    while wants_changed_time < os.path.getmtime(config.wants_file):
        wants_changed_time = os.path.getmtime(config.wants_file)
        fulfill_wants()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
