import sys

from data import collect, logs
import main


def download(video_id):
    if collect.update_video_info(video_id):
        if not logs.chat_log_exists(video_id) or logs.cursor_update(video_id):
            logs.download_log(collect.video_info)
        else:
            print("Existing log is complete.")
    else:
        print("Invalid VOD ID")


if __name__ == '__main__':
    main.setup()
    if collect.client is None:
        collect.client = collect.initialize_client()
    download(sys.argv[1])
