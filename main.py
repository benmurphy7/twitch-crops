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

# TODO: Basic UI (Tkinter or webapp)
# visual emote filtering
# visualize stats
# embedded video player for linking

# Enter VOD ID, show video/emote info, print download status
# Display table of all available emotes (scrollable section) - ability to search for non-case-sensitive contains, also filter by source
# Comma separated list of emotes (case sensitive), with words in quotes for contains
# Display stats such as...
# Largest reactions (per unique emote?)
# Most commot reactions (most windows)
# Total reactions per emote

#TODO: Fix log sync bug causing comments to restart

# TODO: Test continued log updates
# TODO: Support truncating log file? (cleanup fragment cursors)

# TODO: Reactions that last longer should be highlighted in some way?
# Added configurable window size, but no current way to highlight dynamically

# TODO: Improve importance filtering
# Intensity score (higher peak) vs extended "chanting"
# Filter out reactions to spoken emote name? Speech to text library - analyze audio clip before peak

# TODO: Show top-used emotes / stats

# TODO: Association clustering (non k-means)

# TODO: Improve log downloading?
