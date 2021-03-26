import datetime
import os
import sys
import warnings
import webbrowser
from os import path

import matplotlib.pyplot as plt
import mplcursors
import numpy as np
from scipy.signal import find_peaks

import exrex

import collect
import display

download_dir = "Downloads"
images_dir = "Images"
client_info = "clientInfo.txt"


def to_timestamp(secs):
    return str(datetime.timedelta(seconds=secs))


def get_seconds(timestamp):
    h, m, s = timestamp.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def link_time(secs):
    timestamp = to_timestamp(secs)
    h, m, s = timestamp.split(':')
    return str(h) + "h" + str(m) + "m" + str(s) + "s"


def parse_timestamp(line):
    end_idx = line.find("]")
    timestamp = line[1:end_idx]
    return timestamp


def parse_user(line):
    start_idx = line.find(" <") + 2
    end_idx = line.find("> ")
    user = line[start_idx:end_idx]
    return user


def parse_message(line):
    start_idx = line.find("> ") + 2
    message = line[start_idx:]
    return message.strip('\n')


def parse_log(log_path):
    with open(log_path, encoding='utf-8') as f:
        f = f.readlines()
    parsed = []
    for line in f:
        timestamp = parse_timestamp(line)
        user = parse_user(line)
        message = parse_message(line)
        parsed.append((timestamp, user, message))
    return parsed


def round_down(num, divisor):
    return num - (num % divisor)


def max_value_pair(x):
    sorted_x = sorted(x.items(), key=lambda item: item[1], reverse=True)
    if not sorted_x:
        return "null", -1
    return sorted_x[0]


def add_value(k, v, d):
    if k in d:
        d[k] += v
    else:
        d[k] = v
    return d


def timestamp_url(video_id, secs):
    url = "http://twitch.tv/videos/" + video_id + "?t=" + link_time(secs)
    return url


def is_new_max(list, value):
    if list:
        for item in list:
            if value > item:
                return True
    else:
        return True

def filter_match(filter, string):
    if filter[0] == "\"":
        if filter.replace("\"", "") in string:
            return True
    elif filter == string:
        return True
    return False

def get_emote_names(emote, multi_emotes):
    names = []
    if emote in multi_emotes:
        names = multi_emotes[emote]
    else:
        names.append(emote)
    return names

def apply_filter(filter, emotes, multi_emotes):
    matches = []
    for emote in emotes:
        names = get_emote_names(emote, multi_emotes)
        for name in names:
            if filter_match(filter, name):
                matches.append(emote)
                break
    return matches

# Returning (timestamp, count) for each window. Count is just highest count of any emote.
# Should track the prominent emote for each window
def log_emotes(parsed, emotes, window_size, filters=None):
    # Dict of emotes with multiple string codes
    #multi_emotes = {}
    if filters is None:
        filters = []
    log_emotes_list = []
    normal_emotes = []
    filter_list = []
    # Remove duplicates
    [filter_list.append(x) for x in filters if x not in filter_list]

    """
    for emote in emotes:
        names = collect.get_normal_names(emote)
        if len(names) > 1:
            multi_emotes[emote] = names
    """

    for emote in emotes:
        normal_emotes.append(collect.get_normal_name(emote))

    # Check for all emotes containing any words in filters
    if filter_list:
        for filter in filter_list:
            for emote in normal_emotes:
                if filter_match(filter, emote):
                    log_emotes_list.append(emote)
                    break

    else:
        log_emotes_list = emotes

    window_start = 0
    window_data = {}
    times = {}

    # Merging repeated windows
    first_timestamp = ""
    prev_emote = ""
    top_counts = []

    for set in parsed:
        timestamp = set[0]
        user = set[1]
        message = set[2]
        rounded_time = round_down(get_seconds(timestamp), window_size)

        # Start of new window
        if rounded_time > window_start:
            # Get max from ending window
            top_pair = max_value_pair(window_data)
            window_timestamp = to_timestamp(rounded_time)
            top_emote = top_pair[0]
            top_count = top_pair[1]

            # Check for repeated windows and merge
            if top_emote is prev_emote:
                if is_new_max(top_counts, top_count):
                    top_counts.append(top_count)
                    # Move max to first timestamp
                    times[first_timestamp] = (top_emote, top_count)
                # Flatten repeated window
                top_pair = (top_emote, 1)

            else:
                top_counts = []
                first_timestamp = window_timestamp
                times[window_timestamp] = top_pair

            times[window_timestamp] = top_pair
            prev_emote = top_emote
            window_start = rounded_time
            window_data = {}

        # Ignore lines with multiple emote instances (Generally spam, reactions are single emotes)
        if len(message.split(" ")) == 1:
            for emote in log_emotes_list:
                if emote in message:
                        cleaned = message.replace(emote, "", 1)
                        # Message contains more than a single emote - ignore
                        if cleaned != "":
                            continue
                        window_data = add_value(emote, 1, window_data)

    return times, None


def plot_video_data(video_id, times, filters, limit=-1):

    best_times = []
    best_labels = []
    best_values = []

    # Show only top x results
    if limit > 0:
        # [(k,(l,v))]
        sorted_items = sorted(list(times.items()), key=lambda x: x[1][1], reverse=True)
        for index, item in zip(range(limit), sorted_items):
            emote = sorted_items[index][1][0]
            if emote != "null":
                best_times.append(get_seconds(sorted_items[index][0]))
            else:
                break

        #best_times = sorted(best_times, key=get_seconds)
        best_times = sorted(best_times)

        for time in best_times:
            timestamp = to_timestamp(time)
            best_labels.append(times[timestamp][0])
            best_values.append(times[timestamp][1])

    # Show peaks
    else:
        keys = list(times.keys())
        tup_values = list(times.values())
        labels = []
        values = []

        for value in tup_values:
            labels.append(value[0])
            values.append(value[1])

        x = np.array(values)
        peaks, _ = find_peaks(x, prominence=1)  # 12-13 is best, need to test on other logs

        for peak in peaks:
            time = keys[peak]
            best_times.append(time)
            best_labels.append(times[time][0])
            best_values.append(times[time][1])

        avg_val = sum(best_values) / len(best_values)
        plt.axhline(y=avg_val, color='r', linestyle='-')

    x = best_times
    y = best_values


    fig, ax = plt.subplots()
    scatter = ax.scatter(x, y, picker=True)

    fig.canvas.set_window_title("Chat Reactions Over Played Stream")
    #fig.suptitle(video_title + "\nChannel:  " + channel)
    filter_set = ""
    if filters:
        filter_set = ", ".join([str(filter) for filter in filters])
    else:
        filter_set = "All emotes"
    fig.suptitle("Top Reactions: " + filter_set)

    # Show info when hovering cursor
    mplcursors.cursor(plt.gca().get_children(), hover=True).connect(
        "add", lambda sel: sel.annotation.set_text(  # Issue hovering over line
            to_timestamp(best_times[sel.target.index]) + "\n" + best_labels[sel.target.index]))

    gca = plt.gca()
    gca.axes.get_xaxis().set_ticks([])


    #TODO: Fix random "'PickEvent' object has no attribute 'ind'" error
    def on_pick(event):
        try:
            ind = int(event.ind[0])
            plt.plot(x[ind], y[ind], 'ro')
            fig.canvas.draw()
            link_secs = x[ind] - 10
            webbrowser.open(timestamp_url(video_id, link_secs), new=0, autoraise=True)
        except Exception as e:
            #Ignore error for now... not breaking functionality
            #print(e)
            pass

    fig.canvas.mpl_connect('pick_event', on_pick)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        plt.show()


def plot_dict(dict):
    items = dict.items()  # list of (K,V) tuples
    x, y = zip(*items)  # unpack tuples into x, y values
    plt.plot(x, y)
    plt.show()

def chat_log_exists(video_id):
    log_path = download_dir + "/{}.log".format(video_id)
    return path.exists(log_path)

def parse_vod_log(video_id, chat_emotes, custom_filters):
    emotes_list = sorted(list(chat_emotes.keys()), key=len, reverse=True)
    log_path = download_dir + "/{}.log".format(video_id)
    parsed = parse_log(log_path)
    return log_emotes(parsed, emotes_list, 5, custom_filters)

def set_client_info(file):
    client_id, client_secret = collect.get_client_info(file)
    os.system("tcd --client-id {} --client-secret {}".format(client_id, client_secret))

def setup():
    if not os.path.exists(client_info):
        print("Error: clientInfo.txt not found")
        sys.exit(0)
    set_client_info(client_info)

    check_for_dirs = [images_dir, download_dir]
    for dir in check_for_dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)

if __name__ == '__main__':
    setup()
    display.create_qt_window()

#TODO: Fix searching for text emotes ex: ":)" - the regex for these twitch emotes needs to be cleaned
    #Ignore: -? and \\ , map \\&lt\\; to <, \\&gt\\; to >

#TODO: Fix transparent gif issue

#TODO: Basic UI (Tkinter or webapp)
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

#TODO: Reactions that last longer should be highlighted in some way?

#TODO: Show relative spacing in plot view

#TODO: Improve importance filtering
    # Intensity score (higher peak) vs extended "chanting"
    # Filter out reactions to spoken emote name? Speech to text library - analyze audio clip before peak

#TODO: Show top-used emotes / stats

#TODO: Association clustering (non k-means)

#TODO: Improve log downloading?
