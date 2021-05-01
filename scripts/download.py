import sys

from data import collect, logs
import main


def download(video_id):
    if collect.update_video_info(video_id):
        logs.download_log()
    else:
        print("Invalid VOD ID")


if __name__ == '__main__':
    main.setup()
    if collect.client is None:
        collect.client = collect.initialize_client()
    download(sys.argv[1])
