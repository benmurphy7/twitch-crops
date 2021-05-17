import warnings
import webbrowser
from textwrap import wrap

import matplotlib.pyplot as plt
import mplcursors
import numpy as np
import twitch
from matplotlib.backend_bases import PickEvent
from scipy.signal import find_peaks

from common import util


def track_emotes(parsed, emotes, window_size, filters=None):
    if filters is None:
        filters = []
    log_emotes_list = []

    # Check for all emotes containing any words in filters
    try:
        if filters:
            for filter in filters:
                valid = False
                for emote in emotes:
                    if util.filter_match(filter, emote):
                        valid = True
                        log_emotes_list.append(emote)
                if not valid:
                    return None, None, filter

        else:
            log_emotes_list = emotes
    except Exception as e:
        print(e)

    window_start = 0
    window_data = {}
    activity = {}
    message_count = 0

    # Merging repeated windows
    prev_emote = ""
    top_counts = []

    for comment in parsed:
        timestamp = comment[0]
        user = comment[1]
        message = comment[2]
        rounded_time = util.round_down(util.get_seconds(timestamp), window_size)

        # Start of new window
        if rounded_time > window_start:
            # Get max from ending window
            top_item = util.top_item(window_data)
            first_emote_timestamp = top_item[1][1]
            first_message_timestamp = timestamp

            top_pair = (top_item[0], top_item[1][0])
            top_emote = top_pair[0]
            top_count = top_pair[1]

            # Check for repeated windows and merge
            if top_emote is prev_emote:
                if util.is_new_max(top_counts, top_count):
                    top_counts.append(top_count)
                    # Move max to first timestamp
                    activity_data = activity[first_window_timestamp]
                    new_activity_data = ((top_emote, top_count), activity_data[1])
                    activity[first_window_timestamp] = new_activity_data
                # Flatten repeated window
                top_pair = (top_emote, 1)

            else:
                top_counts = []
                first_window_timestamp = first_emote_timestamp

            activity[first_emote_timestamp] = (top_pair, (first_message_timestamp, message_count))
            message_count = 0
            prev_emote = top_emote
            window_start = rounded_time
            window_data = {}

        message_count += 1

        # Ignore lines with multiple emote instances (Generally spam, reactions are single emotes)
        if len(message.split(" ")) == 1:
            for emote in log_emotes_list:
                if emote in message:
                    cleaned = message.replace(emote, "", 1)
                    # Message contains more than a single emote - ignore
                    if cleaned != "":
                        continue
                    util.add_value(window_data, emote, 1, timestamp)

    if len(log_emotes_list) == len(emotes):
        log_emotes_list = []

    return activity, log_emotes_list, None


def plot_video_data(video_info: twitch.helix.Video, activity, filters, limit=50, offset=10):
    best_times = []
    best_labels = []
    best_values = []
    emote_times = {}

    # Message Activity

    messages_x = []
    messages_y = []

    for time in activity:
        messages_x.append(activity[time][1][0])
        messages_y.append(activity[time][1][1])

    # Emote Reactions

    # Show only top x results
    if limit > 0:
        # item : (first_emote_timestamp, (label, value), (window_timestamp, message_count))]
        sorted_items = sorted(list(activity.items()), key=lambda x: x[1][1][1], reverse=True)
        for index, item in zip(range(limit), sorted_items):
            emote = sorted_items[index][1][1][0]
            if emote != "null":
                best_times.append(sorted_items[index][0])
            else:
                break

        best_times = sorted(best_times, key=util.get_seconds)

        for time in best_times:
            best_labels.append(activity[time][0][0])
            best_values.append(activity[time][0][1])

    # Show peaks
    else:
        keys = list(activity.keys())
        tup_values = list(activity.values())
        labels = []
        values = []

        for value in tup_values:
            labels.append(value[0][0])
            values.append(value[0][1])

        emotes_x = np.array(values)
        peaks, _ = find_peaks(emotes_x, prominence=12)  # 12-13 is best, need to test on other logs

        for peak in peaks:
            time = keys[peak]
            if activity[time][0][0] != "null":
                best_times.append(time)
                best_labels.append(activity[time][0][0])
                best_values.append(activity[time][0][1])

    emotes_x = best_times
    emotes_y = best_values

    for i, x in enumerate(best_times):
        emote_times[activity[x][1][0]] = i

    plt.ion()
    fig, ax = plt.subplots(2, figsize=(15, 8))
    fig.canvas.set_window_title(video_info.user_name + " - " + video_info.title)
    fig.tight_layout(pad=3.0)

    ax[0].scatter(emotes_x, emotes_y, picker=True)

    ax[1].plot(messages_x, messages_y, picker=True)
    ax[1].get_yaxis().set_ticks([])

    for axes in ax:
        axes.get_xaxis().set_ticks([])

    r_x = []
    r_y = []

    for i, x in enumerate(emotes_x):
        r_x.append(activity[emotes_x[i]][1][0])
        r_y.append(activity[emotes_x[i]][1][1])

    ax[1].scatter(r_x, r_y, c='green')

    filter_set = ""
    if filters:
        max_filters = 5
        if len(filters) > max_filters:
            for f in range(0, max_filters):
                filter_set += filters[f] + ", "
            filter_set += "... +{} emotes".format(len(filters) - max_filters)
        else:
            filter_set = ", ".join([str(filter) for filter in filters])
    else:
        filter_set = "All emotes"

    ax[0].title.set_text("\n".join(wrap("Top Reactions: " + filter_set)))
    ax[1].title.set_text("Message Activity")

    # Show info when hovering cursor
    mplcursors.cursor(ax[0].get_children(), hover=True).connect(
        "add", lambda sel: sel.annotation.set_text(
            best_times[sel.target.index] + "\n" + best_labels[sel.target.index]))

    mplcursors.cursor(ax[1].get_children()[0], hover=True).connect(
        "add", lambda sel: sel.annotation.set_text(
            best_times[sel.target.index] + "\n" + best_labels[sel.target.index]))

    # TODO: Fix random "'PickEvent' object has no attribute 'ind'" error
    def on_pick(event: PickEvent):
        try:
            axes = event.artist.axes
            ind = int(event.ind[0])
            if axes == ax[1]:
                if messages_x[ind] in emote_times:
                    ind = emote_times[messages_x[ind]]
                else:
                    return
            ax[0].plot(emotes_x[ind], emotes_y[ind], 'ro')
            ax[1].plot(r_x[ind], r_y[ind], 'ro')
            fig.canvas.draw()
            timestamp = emotes_x[ind]
            link_secs = util.get_seconds(timestamp) - offset
            webbrowser.open(util.timestamp_url(video_info.id, link_secs), new=0, autoraise=True)
        except Exception as e:
            # Ignore error for now... not breaking functionality
            # print(e)
            pass

    fig.canvas.mpl_connect('pick_event', on_pick)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        plt.show()


def plot_dict(dict):
    items = dict.items()
    x, y = zip(*items)
    plt.plot(x, y)
    plt.show()
