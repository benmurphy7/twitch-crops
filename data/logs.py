import ntpath
import os
import sys
import traceback
from datetime import timedelta
from os import path
from pathlib import Path

from PyQt5.QtCore import pyqtSignal

from data import analyze, collect
from common import util, config


def get_log_path(video_id):
    return config.download_dir + "/{}.log".format(video_id)


def chat_log_exists(video_id):
    log_path = get_log_path(video_id)
    return path.exists(log_path) and os.stat(log_path).st_size > 0


def get_existing_logs():
    log_list = []
    for file in sorted(Path(config.download_dir).iterdir(), key=os.path.getmtime, reverse=True):
        filename = ntpath.basename(file)
        if filename.endswith(".log"):
            log_list.append(filename)
    return log_list


def parse_log(log_path):
    with open(log_path, encoding='utf-8') as f:
        f = f.readlines()
    parsed = []
    for line in f:
        if "<" in line:
            timestamp = util.parse_timestamp(line)
            user = util.parse_user(line)
            message = util.parse_message(line)
            parsed.append((timestamp, user, message))
    return parsed


def parse_vod_log(video_id, chat_emotes, custom_filters, window):
    emotes_list = sorted(list(chat_emotes.keys()), key=len, reverse=True)
    log_path = get_log_path(video_id)
    parsed = parse_log(log_path)
    return analyze.track_emotes(parsed, emotes_list, window, custom_filters)


def log_end_time(video_id):
    last_line = get_last_lines(get_log_path(video_id), n=1)[0]
    return util.parse_timestamp(last_line)


def get_log_file():
    return get_log_path(collect.video_info.id)


def check_for_updates(video_id):
    # Checking if log exists is redundant for now, but may be needed if called from elsewhere
    if chat_log_exists(video_id):
        last_time = log_end_time(video_id)
        video_time = util.link_time_to_timestamp(collect.video_info.duration)
        if util.get_seconds(last_time) < util.get_seconds(video_time):
            download_log()
            return True

    return False


def get_last_lines(file, n=2):
    list_of_lines = []
    with open(file, 'rb') as f:
        f.seek(0, os.SEEK_END)
        buffer = bytearray()
        pointer_location = f.tell()
        while pointer_location >= 0:
            f.seek(pointer_location)
            pointer_location = pointer_location - 1
            new_byte = f.read(1)
            if new_byte == b'\n':
                # Decode and remove remaining EOL characters (Windows)
                line = buffer.decode(errors='replace')[::-1].replace("\r", "")
                # Ignore empty lines
                if line:
                    list_of_lines.append(line)
                if len(list_of_lines) == n:
                    return list_of_lines
                buffer = bytearray()
            else:
                buffer.extend(new_byte)
    return list_of_lines


def get_or_make_temp_dir():
    temp_dir = "../temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir


def update_fragment(cursor, comments, idx):
    new_block = ''
    for i in range(idx, len(comments)):
        line = format_comment(comments[i])
        new_block += line
    new_block += cursor + "\n"
    with open(get_log_file(), 'a+', encoding='utf-8') as file:
        file.write(new_block)


def fragment_change(cursor, last_saved_comment):
    comments = get_comments(cursor)
    last_fragment_comment = format_comment(comments[-1])
    if last_fragment_comment == last_saved_comment:
        return False
    for x, comment in enumerate(comments):
        line = format_comment(comment)
        if line == last_fragment_comment:
            update_fragment(cursor, comments, x)
    return True


def next_cursor(cursor):
    try:
        fragment = collect.video_info.comments.fragment(cursor)
        if '_next' in fragment:
            return fragment['_next']
        else:
            return ''
    except:
        return ''


def relative_timestamp(seconds):
    delta = timedelta(seconds=seconds)
    delta = delta - timedelta(microseconds=delta.microseconds)
    return str(delta)


def format_comment(comment):
    timestamp = relative_timestamp(float(comment['content_offset_seconds']))
    commenter = comment['commenter']['display_name']
    message = comment['message']['body']
    return "[{}] <{}> {}\n".format(timestamp, commenter, message)


def download_progress(video_id, comment, end, signal: pyqtSignal = None):
    current = float(comment['content_offset_seconds'])
    status = '( Downloading )  [ {} ]  -  {}%\r'.format(video_id, '%.2f' % min(current * 10 / end * 10, 100.00))

    if signal is not None:
        signal.emit(status)
    else:
        sys.stdout.flush()
        sys.stdout.write(status)


def get_comments(cursor):
    fragment = collect.video_info.comments.fragment(cursor)
    return fragment['comments']


def get_fragment(comments, cursor):
    return comments.fragment(cursor)


# Download, appending to existing log if exists
def download_log(video_info, signal: pyqtSignal = None):
    video_id = video_info.id
    file = get_log_path(video_id)
    cursor = cursor_update(video_id)
    end = util.link_time_to_seconds(video_info.duration)

    try:
        with open(file, 'a+', encoding='utf-8') as file:
            while True:
                chunk = ''
                fragment = get_fragment(video_info.comments, cursor)
                comments = fragment['comments']
                download_progress(video_id, comments[-1], end, signal)
                for comment in comments:
                    chunk += format_comment(comment)
                if '_next' in fragment:
                    cursor = fragment['_next']
                else:
                    pass
                chunk += cursor + "\n"
                file.write(chunk)
                if '_next' not in fragment:
                    break
    except Exception:
        traceback.print_exception(*sys.exc_info())


def cursor_update(video_id):
    try:
        cursor = ''
        if chat_log_exists(video_id):
            lines = get_last_lines(get_log_path(video_id), n=2)
            cursor = lines[0].replace("\n", "")
            last_saved_comment = lines[1] + "\n"
            split = cursor.split(" ")

            # Old format, remove in future
            if len(split) == 2:
                cursor = split[1].replace("\n", "")
            # Invalid cursor format (old file) - can't perform update
            elif len(split) > 2:
                cursor = ''

            if cursor:
                if fragment_change(cursor, last_saved_comment):
                    pass
                cursor = next_cursor(cursor)

        return cursor

    except Exception as e:
        print(e)
        return ''
