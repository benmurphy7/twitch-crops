print("Patching gevent...")
import gevent.monkey
gevent.monkey.patch_all()
print("Patch complete.\n")

import os
import sys
import time

print("Importing collect...")
from data import collect
print("Importing display...")
from app import display
from common import config
print("\nMain imports complete.")


def setup():
    if not os.path.exists(config.client_info):
        print("Error: {} not found".format(config.client_info))
        time.sleep(3)
        sys.exit(0)

    check_for_dirs = [config.images_dir, config.download_dir]
    for dir in check_for_dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)


if __name__ == '__main__':
    setup()
    collect.client = collect.initialize_client()
    display.create_qt_window()

# TODO: Improve analysis

# TODO: Show top-used emotes / stats

# TODO: Association clustering (non k-means)

# TODO: Improve log downloading? - limited by Twitch API
