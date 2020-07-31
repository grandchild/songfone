import os
import sys

from config import config
from database import update_database
from wants import fulfill_wants


def main(config_file=None):
    try:
        config.load(config_file or "songfone.conf")
    except Exception as err:
        print(
            f"Error, config file not loaded ({type(err).__name__}): {err}",
            file=sys.stderr,
        )
        return
    try:
        config.make_output()
    except Exception as err:
        print(f"Error, cannot create output directory or file: {err}", file=sys.stderr)
        return
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
