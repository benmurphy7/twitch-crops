import numpy as np
import tcd
import os
from os import path
import datetime
import operator
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from scipy.signal import find_peaks
import webbrowser
import collect
import mplcursors


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
    if len(sorted_x) < 1:
        return "null", -1
    return sorted_x[0]


def add_value(k, v, d):
    if k in d:
        d[k] += v
    else:
        d[k] = v
    return d

def timestamp_url(secs):
    url = "http://twitch.tv/videos/" + video_id + "?t=" + link_time(secs)
    return url


# Returning (timestamp, count) for each window. Count is just highest count of any emote.
# Should track the prominent emote for each window
def log_emotes(parsed, emotes, window, filter_list=[]):
    log_emotes_list = []
    # Check for all emotes containing any words in filters
    if len(filter_list) > 0:
        for emote in emotes:
            for filter in filter_list:
                if filter in emote:
                    log_emotes_list.append(emote)
    else:
        log_emotes_list = emotes

    window_start = 0
    window_data = {}
    times = {}
    for set in parsed:
        timestamp = set[0]
        user = set[1]
        message = set[2]
        rounded_time = round_down(get_seconds(timestamp), window)

        # Start of new window
        if rounded_time > window_start:
            # Get max from ending window
            top_pair = max_value_pair(window_data)
            window_timestamp = to_timestamp(rounded_time)
            # Save tuple as value in future
            times[window_timestamp] = top_pair
            window_start = rounded_time
            window_data = {}
        """
        if len(filter_list) > 0:
            for word in filter_list:
                if word in message:
                    cleaned = message.replace(word, "", 1)
                    # Message contains more than a single emote - ignore
                    if cleaned != "":
                        break
                    window_data = add_value(word, 1, window_data)
        """
        # Ignore lines with multiple emote instances (Generally spam, reactions are single emotes)
        for emote in log_emotes_list:
            if emote in message:
                cleaned = message.replace(emote, "", 1)
                # Message contains more than a single emote - ignore
                if cleaned != "":
                    break
                window_data = add_value(emote, 1, window_data)

    return times


def show_peaks(times, limit=-1):

    best_times = []
    best_labels = []
    best_values = []

    # Show only top x results
    if limit > 0:
        # [(k,(l,v))]
        sorted_items = sorted(list(times.items()), key=lambda x: x[1][1], reverse=True)
        while len(best_times) < limit:
            # best_labels.append(sorted_items[len(best_labels)][1][0])
            # best_values.append(sorted_items[len(best_values)][1][1])
            best_times.append(sorted_items[len(best_times)][0])

        best_times = sorted(best_times)

        for time in best_times:
            best_labels.append(times[time][0])
            best_values.append(times[time][1])

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
    ax.scatter(x, y, picker=True)
    fig.canvas.set_window_title("Chat Reactions Over Played Stream")
    fig.suptitle(video_title + "\nChannel:  "+ channel)

    #plt.scatter(x, y)

    # Label points
    """
    for x, y in zip(x, y):
        label = f"({x})"

        plt.annotate(label,  # this is the text
                     (x, y),  # this is the point to label
                     textcoords="offset points",  # how to position the text
                     xytext=(0, 10),  # distance from text to points (x,y)
                     ha='center')  # horizontal alignment can be left, right or center
    """

    # Show info when hovering cursor
    mplcursors.cursor(hover=True).connect(
        "add", lambda sel: sel.annotation.set_text(  # Issue hovering over line
            best_times[sel.target.index] + "\n" + best_labels[sel.target.index]))

    gca = plt.gca()
    gca.axes.get_xaxis().set_ticks([])

    #TODO: Fix random "'PickEvent' object has no attribute 'ind'" error
    def on_pick(event):
        try:
            ind = int(event.ind[0])
            timestamp = x[ind]
            link_secs = get_seconds(timestamp) - 10
            webbrowser.open(timestamp_url(link_secs), new=0, autoraise=True)
        except:
            #Ignore error for now... not breaking functionality
            pass

    fig.canvas.mpl_connect('pick_event', on_pick)

    plt.show()


def plot_dict(dict):
    items = dict.items()  # list of (K,V) tuples
    x, y = zip(*items)  # unpack tuples into x, y values
    plt.plot(x, y)
    plt.show()


if __name__ == '__main__':
    download_dir = "./Downloads"
    video_id = "888950607"
    log_path = download_dir + "/{}.log".format(video_id)

    if not path.exists(log_path):
        print("Chat log not found. Downloading...")
        os.system("tcd --video {} --format irc --output {}".format(video_id, download_dir))
    else:
        print("Log already exists")

    emotes_list, video_title, channel = collect.getEmotesList(video_id)
    custom_filters = ["LULW", "KEKW"]

    print("Analyzing chat...")

    # parsed : [timestamp, user, message]
    parsed = parse_log(log_path)
    data = log_emotes(parsed, emotes_list, 5, custom_filters)
    # plot_dict(data)
    # times = parse(log_path, emotes_list)
    # For smaller streams, clustering by time is necessary since overlap is rare
    # Try grouping counts by x seconds (5?) - larger span could be a problem with spam
    # Get the most used emote within that timeframe, save as K = timestamp, V = (count,emote)
    # Result - thrown off by spam, difficult to get moment pinpoint from plot
    # smoothed = smoothData(times, 15)
    show_peaks(data, 50)

    # print(toTimestamp(max(times.items(), key=operator.itemgetter(1))[0]))
    # Very slow - need to process this before plotting
    # plotDict(times)

#TODO: Merge consecutive reaction timeblocks
    # Improve time offset for links

#TODO: Improve importance filtering
    # Intensity score (higher peak) vs extended "chanting"
    # Filter out reactions to spoken emote name? Speech to text library - analyze audio clip before peak

#TODO: Show top-used emotes / stats

#TODO: Association clustering (non k-means)

#TODO: Basic UI (Tkinter or webapp)
    # visual emote filtering
    # visualize stats
    # embedded video player for linking

#TODO: Improve log downloading?
