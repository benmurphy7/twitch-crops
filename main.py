import os
import sys

from data import collect
from app import display
from common import config


def setup():
    if not os.path.exists(config.client_info):
        print("Error: {} not found".format(config.client_info))
        sys.exit(0)

    check_for_dirs = [config.images_dir, config.download_dir]
    for dir in check_for_dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)


if __name__ == '__main__':
    setup()
    collect.client = collect.initialize_client()
    display.create_qt_window()

# TODO: Existing VOD combo selection

# TODO: Improve analysis

# TODO: Show top-used emotes / stats

# TODO: Association clustering (non k-means)

# TODO: Improve log downloading? - limited by Twitch API
