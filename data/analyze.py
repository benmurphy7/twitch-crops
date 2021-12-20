import warnings
import webbrowser
from textwrap import wrap

import matplotlib
import matplotlib.pyplot as plt
import mplcursors
import mpld3 as mpld3
import numpy as np
import twitch
from matplotlib.backend_bases import PickEvent
from mpld3 import plugins, utils
from mpld3.plugins import PluginBase
from mpld3.utils import get_id
from scipy.signal import find_peaks

from app import display
from common import util

clip_margin = 0
emote_avg = 0


class ClickInfo(mpld3.plugins.PluginBase):
    """mpld3 Plugin for getting info on click        """

    JAVASCRIPT = """
    mpld3.register_plugin("clickinfo", ClickInfo);
    ClickInfo.prototype = Object.create(mpld3.Plugin.prototype);
    ClickInfo.prototype.constructor = ClickInfo;
    ClickInfo.prototype.requiredProps = ["id", "urls"];
    function ClickInfo(fig, props){
        mpld3.Plugin.call(this, fig, props);
        mpld3.insert_css("#" + fig.figid + " path.clicked",
                         {"fill": "black"});
    };

    ClickInfo.prototype.draw = function(){
        var obj = mpld3.get_element(this.props.id);
        urls = this.props.urls;
        obj.elements().on("mousedown.callout",
                          function(d, i){ 
                            d3.select(this).classed("clicked", true);
                            window.open(urls[i], 'TwitchCrops')});
    }
    """

    def __init__(self, points, urls, css=None):
        self.points = points
        self.urls = urls
        self.css_ = css or ""
        if isinstance(points, matplotlib.lines.Line2D):
            suffix = "pts"
        else:
            suffix = None
        self.dict_ = {"type": "clickinfo",
                      "id": mpld3.utils.get_id(points, suffix),
                      "urls": urls}


class PointHTMLTooltip(PluginBase):
    """A Plugin to enable an HTML tooltip:
    formated text which hovers over points.

    Parameters
    ----------
    points : matplotlib Collection or Line2D object
        The figure element to apply the tooltip to
    labels : list
        The labels for each point in points, as strings of unescaped HTML.
    targets : list
        The urls that each point will open when clicked.
    hoffset, voffset : integer, optional
        The number of pixels to offset the tooltip text.  Default is
        hoffset = 0, voffset = 10
    css : str, optional
        css to be included, for styling the label html if desired
    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> from mpld3 import fig_to_html, plugins
    >>> fig, ax = plt.subplots()
    >>> points = ax.plot(range(10), 'o')
    >>> labels = ['<h1>{title}</h1>'.format(title=i) for i in range(10)]
    >>> plugins.connect(fig, PointHTMLTooltip(points[0], labels))
    >>> fig_to_html(fig)
    """

    JAVASCRIPT = """
    mpld3.register_plugin("htmltooltip", HtmlTooltipPlugin);
    HtmlTooltipPlugin.prototype = Object.create(mpld3.Plugin.prototype);
    HtmlTooltipPlugin.prototype.constructor = HtmlTooltipPlugin;
    HtmlTooltipPlugin.prototype.requiredProps = ["id"];
    HtmlTooltipPlugin.prototype.defaultProps = {labels:null,
                                                target:null,
                                                hoffset:0,
                                                voffset:10,
                                                targets:null};
    function HtmlTooltipPlugin(fig, props){
        mpld3.Plugin.call(this, fig, props);
        mpld3.insert_css("#" + fig.figid + " path.hovered",
                        {"fill-opacity": "0.5 !important",
                        "stroke-opacity": "1.0 !important",
                        "stroke": "black !important"});
        mpld3.insert_css("#" + fig.figid + " path.clicked",
                        {"fill-opacity": "0.3 !important",
                        "stroke-opacity": "1.0 !important",
                        "fill": "red !important",
                        "stroke": "red !important"});
                         
    };

    HtmlTooltipPlugin.prototype.draw = function(){
        var obj = mpld3.get_element(this.props.id);
        var labels = this.props.labels;
        var targets = this.props.targets;
        var tooltip = d3.select("body").append("div")
            .attr("class", "mpld3-tooltip")
            .style("position", "absolute")
            .style("z-index", "10")
            .style("visibility", "hidden");

        obj.elements()
        //"mouseover"
            .on("mouseenter", function(d, i){
             d3.select(this).classed("hovered", true);
                /*tooltip.html(labels[i])
                    .style("visibility", "visible");*/
            })
            .on("mousemove", function(d, i){
                tooltip
                .style("top", d3.event.pageY + this.props.voffset + "px")
                .style("left",d3.event.pageX + this.props.hoffset + "px");
            }.bind(this))
            .on("mousedown.callout", function(d, i){
                d3.select(this).classed("clicked", true);
                window.open(targets[i],'TwitchCrops');
            })
            //"mouseout"
            .on("mouseleave", function(d, i){
            d3.select(this).classed("hovered", false);
                /*tooltip.style("visibility", "hidden");*/
            });
    };
    """

    def __init__(self, points, labels=None, targets=None,
                 hoffset=0, voffset=10, css=None):
        self.points = points
        self.labels = labels
        self.targets = targets
        self.voffset = voffset
        self.hoffset = hoffset
        self.css_ = css or ""
        if isinstance(points, matplotlib.lines.Line2D):
            suffix = "pts"
        else:
            suffix = None
        self.dict_ = {"type": "htmltooltip",
                      "id": get_id(points, suffix),
                      "labels": labels,
                      "targets": targets,
                      "hoffset": hoffset,
                      "voffset": voffset}


def track_emotes(parsed, emotes, window_size, filters=None, valid_emotes_only=True, single_emotes_only=True):
    if filters is None:
        filters = []
    log_emotes_list = []

    """
    valid_emotes_only = False
    single_emotes_only = False
    if display.window.validEmotesOnly.checkState(0) == 2:
        valid_emotes_only = True
        if display.window.singleEmotesOnly.checkState(0) == 2:
            single_emotes_only = True
    """

    # Check for all emotes containing any words in filters
    try:
        if filters:
            for filter in filters:
                if valid_emotes_only:
                    valid = False
                    for emote in emotes:
                        if util.filter_match(filter, emote):
                            valid = True
                            if emote not in log_emotes_list:
                                log_emotes_list.append(emote)
                    if not valid:
                        return None, None, filter, None
                else:
                    log_emotes_list.append(filter)
        else:
            log_emotes_list = emotes
    except Exception as e:
        print(e)

    stats = {}
    total_messages = 0
    total_emotes = 0
    total_windows = 0

    window_start = 0
    window_data = {}
    activity = {}
    message_count = 0
    first_message_timestamp = ""

    # Merging repeated windows
    prev_emote = ""

    for comment in parsed:
        timestamp = comment[0]
        if not first_message_timestamp:
            first_message_timestamp = timestamp
        user = comment[1]
        message = comment[2]
        rounded_time = util.round_down(util.get_seconds(timestamp), window_size)

        total_messages += 1

        # Start of new window
        if rounded_time > window_start:

            total_windows += 1

            # Get max from ending window
            top_item = util.top_item(window_data)
            first_emote_timestamp = top_item[1][1]
            if not first_emote_timestamp:
                first_emote_timestamp = first_message_timestamp
            total_value = util.total_value(window_data)

            top_emote = top_item[0]
            top_count = top_item[1][0]
            top_emote_data = [top_emote, top_count, total_value]

            # Check for repeated windows and merge
            # TODO: Assign top count to window with highest message count?
            # TODO: Find max chat message counts and shift top emotes to that peak if close?
            if top_emote is prev_emote:
                if top_count > emote_max:
                    emote_max = top_count
                    activity[previous_timestamp] = [[top_emote, 0, 0], [first_message_timestamp, message_count]]
                else:
                    # Flatten non-max window
                    top_emote_data = [top_emote, 0, 0]

            else:
                emote_max = top_count

            activity[first_emote_timestamp] = [top_emote_data, [first_message_timestamp, message_count]]

            first_message_timestamp = timestamp
            message_count = 0
            prev_emote = top_emote
            window_start = rounded_time
            window_data = {}
            previous_timestamp = first_emote_timestamp

        message_count += 1

        tokens = message.split(" ")

        # Filter Matching
        if single_emotes_only:
            if len(tokens) == 1:
                for emote in log_emotes_list:
                    if emote in message:
                        cleaned = message.replace(emote, "", 1)
                        # Message contains more than emote name - ignore
                        if cleaned != "":
                            continue
                        util.add_value(window_data, emote, 1, timestamp)
                        total_emotes += 1
        else:
            if valid_emotes_only:
                for token in tokens:
                    for emote in log_emotes_list:
                        if emote == token:
                            util.add_value(window_data, emote, 1, timestamp)
                            total_emotes += 1
            else:
                # TODO: Optimize contains search for phrases
                for emote in log_emotes_list:
                    if util.filter_match(emote, message):
                        util.add_value(window_data, emote, 1, timestamp)
                        total_emotes += 1

        """
        # Count all unique emotes - analysis is too slow
        for emote in log_emotes_list:
            if emote in message:
                util.add_value(window_data, emote, 1, timestamp)
        """

    if not filters:
        log_emotes_list = []

    stats["total_messages"] = total_messages
    stats["total_emotes"] = total_emotes
    stats["total_windows"] = total_windows
    stats["avg_messages"] = total_messages / total_windows
    stats["avg_emotes"] = total_emotes / total_windows

    global emote_avg
    emote_avg = total_emotes / total_windows

    return activity, log_emotes_list, None, stats


def plot_video_data(video_info: twitch.helix.Video, activity, filters, stats, limit=0, offset=10, html=False):
    global clip_margin
    clip_margin = offset

    best_emote_times = []
    best_msg_times = []
    best_labels = []

    # Activity

    messages_x = []
    messages_y = []

    emote_act_x = []
    emote_act_y = []

    for time in activity:
        entry = activity[time]
        messages_x.append(entry[1][0])
        messages_y.append(entry[1][1])
        emote_act_x.append(entry[1][0])
        emote_act_y.append(entry[0][1])

    # Emote Reactions

    # Show only top x results
    if limit > 0:
        # Sort by reactions

        # Reference -> item : (first_emote_timestamp, [[label, value, total_val], [window_timestamp, message_count]])
        sorted_items = sorted(list(activity.items()), key=lambda x: x[1][0][1], reverse=True)
        for item in sorted_items:
            if len(best_emote_times) < limit:
                emote = item[1][0][0]
                count = item[1][0][1]
                # TODO: Handle non-max windows in chain - potential exclusion and non-peak points
                if emote != "null" and count > 0:
                    best_emote_times.append(item[0])

        best_emote_times = sorted(best_emote_times, key=util.get_seconds)

        for time in best_emote_times:
            best_labels.append(activity[time][0][0])

        # Sort by message activity
        visited = []
        sorted_items = sorted(list(activity.items()), key=lambda x: x[1][1][1], reverse=True)
        for item in sorted_items:
            if len(best_msg_times) < limit:
                visited.append(item[0])
                if not linked_window(activity, item[0], visited):
                    best_msg_times.append(item[0])

        best_msg_times = sorted(best_msg_times, key=util.get_seconds)

    else:
        """
        avg_messages = stats["avg_messages"]
        avg_emotes = stats["avg_emotes"]

        for time in activity:
            entry = activity[time]
            if(entry[0][1] > avg_emotes or entry[1][1] > avg_messages):
                # Message count peaks may not contain a valid emote
                best_emote_times.append(time)
                best_labels.append(entry[0][0])
        """

        # Peak finding
        keys = list(activity.keys())
        tup_values = list(activity.values())
        labels = []
        emote_counts = []
        message_counts = []

        for value in tup_values:
            labels.append(value[0][0])
            emote_counts.append(value[0][1])
            message_counts.append(value[1][1])

        emotes_x = np.array(message_counts)
        peaks, _ = find_peaks(emotes_x, prominence=11)  # 12-13 seems best

        for peak in peaks:
            time = keys[peak]
            if activity[time][0][0] != "null":
                best_emote_times.append(time)
                best_labels.append(activity[time][0][0])

    emotes_x = best_emote_times

    fig, axes = plt.subplots(2, figsize=(15, 8))
    fig.tight_layout(pad=3.0)

    plot_title = video_info.user_name + " - " + video_info.title

    if not html:
        plt.ion()
        fig.canvas.set_window_title(plot_title)
    else:
        plt.title(plot_title)

    for ax in axes:
        ax.get_xaxis().set_ticks([])
        ax.set_axisbelow(True)
        ax.grid()
        # ax.get_xaxis().set_ticks(generate_ticks(messages_x, 100))
        # ax.get_xaxis().set_ticks(np.arange(0, len(messages_x), 100))

        # ax.set_xticklabels(ax.get_xticks(), rotation=45)

        # [l.set_visible(False) for (i, l) in enumerate(ax.get_xaxis().get_ticklabels()) if i % 100 != 0]

    axes[0].plot(emote_act_x, emote_act_y, picker=True, c='green', zorder=0)
    axes[1].plot(messages_x, messages_y, picker=True, c='orange', zorder=0)

    e_x = []
    e_y = []
    m_x = []
    m_y = []

    for time in emotes_x:
        entry = activity[time]
        e_x.append(entry[1][0])
        e_y.append(entry[0][1])

    for time in best_msg_times:
        entry = activity[time]
        m_x.append(entry[1][0])
        m_y.append(entry[1][1])

    # Draw selectable scatter plots
    top_points = axes[0].scatter(e_x, e_y, picker=True, marker='d', c='gold', s=50, zorder=1)
    bot_points = axes[1].scatter(m_x, m_y, picker=True, marker='o', c='blue', s=30, zorder=1)

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

    axes[0].set_title("\n".join(wrap("Top CROPS: " + filter_set)), fontsize=18, fontweight="bold")
    axes[1].set_title("Message Activity", fontsize=18, fontweight="bold")

    artists = []

    # Show info when hovering cursor
    mpl_label(axes[0], best_emote_times, artists, activity, 0)
    mpl_label(axes[1], best_msg_times, artists, activity, 1)

    axes[0].autoscale(False)
    axes[1].autoscale(False)

    # TODO: Fix random "'PickEvent' object has no attribute 'ind'" error
    def on_pick(event: PickEvent):
        try:
            if event.artist not in artists:
                return
            event_axes = event.artist.axes
            ind = int(event.ind[0])
            if event_axes == axes[0]:
                axes[0].plot(e_x[ind], e_y[ind], 'rd')
                timestamp = emotes_x[ind]
            if event_axes == axes[1]:
                axes[1].plot(m_x[ind], m_y[ind], 'ro')
                timestamp = best_msg_times[ind]
            fig.canvas.draw()
            link_secs = util.get_seconds(timestamp) - offset
            webbrowser.open(util.timestamp_url(video_info.id, link_secs), new=0, autoraise=True)

            """
            # Output to easily copy clip start/end
            print("Start time: {}".format(util.strfdelta(timedelta(0, link_secs), '%H:%M:%S')))
            # Add extra time for extended reactions
            print("Start time: {}".format(util.strfdelta(timedelta(0, link_secs + (offset * 2)), '%H:%M:%S')))
            # Reaction score - relative score (reaction score / avg emotes per window)
            print("{}-{:.2f}-".format(e_y[ind], e_y[ind] / emote_avg))
            """

        except Exception as e:
            # Ignore error for now... not breaking functionality
            # print(e)
            pass

    fig.canvas.mpl_connect('pick_event', on_pick)

    # Render for webpage
    top_urls = []
    bot_urls = []
    top_labels = []
    bot_labels = []
    try:
        for idx, point in enumerate(e_x):
            timestamp = emotes_x[idx]
            link_secs = util.get_seconds(timestamp) - offset
            top_urls.append(util.timestamp_url(video_info.id, link_secs))

            top_labels.append(set_text(best_emote_times, activity, idx, 0))

        for idx, point in enumerate(m_x):
            timestamp = best_msg_times[idx]
            link_secs = util.get_seconds(timestamp) - offset
            bot_urls.append(util.timestamp_url(video_info.id, link_secs))

            bot_labels.append(set_text(best_msg_times, activity, idx, 1))

        # Works for multiple point sets, but tool tip isn't formatted well
        plugins.connect(fig, PointHTMLTooltip(top_points, top_labels, top_urls))
        plugins.connect(fig, PointHTMLTooltip(bot_points, bot_labels, bot_urls))
        plugins.connect(fig, plugins.PointLabelTooltip(top_points, top_labels))
        plugins.connect(fig, plugins.PointLabelTooltip(bot_points, bot_labels))

        # Broken (won't map multiple point sets correctly across multiple ClickInfo objects)
        #plugins.connect(fig, ClickInfo(top_points, top_urls))
        #plugins.connect(fig, ClickInfo(bot_points, bot_urls))

        #Broken (maximum recursion depth exceeded)
        #plugins.connect(fig, plugins.PointClickableHTMLTooltip(top_points, top_labels, top_urls))
        #plugins.connect(fig, plugins.PointClickableHTMLTooltip(bot_points, bot_labels, bot_urls))

    except Exception as e:
        print(e)

    # plugins.connect(fig, ClickInfo(top_points, top_urls))

    if html:
        print("Creating html chart")
        try:
            html_str = mpld3.fig_to_html(fig)
            return html_str
            #html_file = open("templates/chart.html", "w")
            #html_file.write(html_str)
            #html_file.close()
        except Exception as e:
            print(e)

    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            plt.show()


def mpl_label(axis, times, artists, activity, plot):
    artists.append(axis.get_children()[0])
    mplcursors.cursor(axis.get_children()[0], hover=True).connect(
        "add", lambda sel: sel.annotation.set_text(set_text(times, activity, sel.target.index, plot)))


def generate_ticks(x_data, interval):
    ticks = []
    tick = 0
    while tick < len(x_data):
        val = x_data[tick]
        ticks.append(str(x_data[tick]))
        tick += interval

    return ticks


def set_text(times, activity, index, plot):
    text = ""
    if plot == 0:
        text += activity[times[index]][0][0] + "\n"
    text += times[index]
    return text


def linked_window(activity: dict, time, visited):
    keys = list(activity.keys())
    index = keys.index(time)
    for n in get_neighbors(keys, index, 2):
        if n in visited:
            return True
    return False


def get_neighbors(list, index, radius):
    neighbors = []
    for r in range(1, radius + 1):
        i = index - r
        if i >= 0:
            neighbors.append(list[i])
        i = index + r
        if i < len(list):
            neighbors.append(list[i])
    return neighbors


def plot_dict(dict):
    items = dict.items()
    x, y = zip(*items)
    plt.plot(x, y)
    plt.show()
