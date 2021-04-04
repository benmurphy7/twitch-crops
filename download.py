import sys

import collect
import log
import main


def download(video_id):
    if collect.update_video_info(video_id):
        log.download_log()
    else:
        print("Invalid VOD ID")


if __name__ == '__main__':
    main.setup()
    if collect.client is None:
        collect.client = collect.initialize_client()
    download(sys.argv[1])
