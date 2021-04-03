# Returning (timestamp, count) for each window. Count is just highest count of any emote.
# Should track the prominent emote for each window
import warnings
import webbrowser

import matplotlib.pyplot as plt
import mplcursors
import numpy as np
from scipy.signal import find_peaks

import collect
import util


def track_emotes(parsed, emotes, window_size, filters=None):
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
        normal_emotes.append(util.get_normal_name(emote))

    # Check for all emotes containing any words in filters
    if filter_list:
        for filter in filter_list:
            valid = False
            for emote in normal_emotes:
                if util.filter_match(filter, emote):
                    valid = True
                    log_emotes_list.append(emote)
                    break
            if not valid:
                return None, filter

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
        rounded_time = util.round_down(util.get_seconds(timestamp), window_size)

        # Start of new window
        if rounded_time > window_start:
            # Get max from ending window
            top_pair = util.max_value_pair(window_data)
            window_timestamp = util.to_timestamp(rounded_time)
            top_emote = top_pair[0]
            top_count = top_pair[1]

            # Check for repeated windows and merge
            if top_emote is prev_emote:
                if util.is_new_max(top_counts, top_count):
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
                        window_data = util.add_value(emote, 1, window_data)

    return times, None

def plot_video_data(video_id, times, filters, limit=50, offset=10):

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
                best_times.append(sorted_items[index][0])
            else:
                break

        best_times = sorted(best_times, key=util.get_seconds)

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
            best_times[sel.target.index] + "\n" + best_labels[sel.target.index]))

    gca = plt.gca()
    gca.axes.get_xaxis().set_ticks([])


    #TODO: Fix random "'PickEvent' object has no attribute 'ind'" error
    def on_pick(event):
        try:
            ind = int(event.ind[0])
            plt.plot(x[ind], y[ind], 'ro')
            fig.canvas.draw()
            timestamp = x[ind]
            link_secs = util.get_seconds(timestamp) - offset
            webbrowser.open(util.timestamp_url(video_id, link_secs), new=0, autoraise=True)
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