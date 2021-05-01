import os
import sys

import collect
import display

download_dir = "Downloads"
images_dir = "Images"
client_info = "clientInfo.txt"


def setup():
    if not os.path.exists(client_info):
        print("Error: clientInfo.txt not found")
        sys.exit(0)

    check_for_dirs = [images_dir, download_dir]
    for dir in check_for_dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)


if __name__ == '__main__':
    setup()
    collect.client = collect.initialize_client()
    display.create_qt_window()

# TODO: Image download status

# TODO: Improve analysis

# TODO: Show top-used emotes / stats

# TODO: Association clustering (non k-means)

# TODO: Improve log downloading? - limited by Twitch API
