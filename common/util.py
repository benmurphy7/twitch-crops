import datetime
import html
from string import Template

import exrex


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


def to_timestamp(secs):
    return str(datetime.timedelta(seconds=secs))


def get_seconds(timestamp):
    h, m, s = timestamp.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def link_time(secs):
    timestamp = to_timestamp(secs)
    h, m, s = timestamp.split(':')
    return str(h) + "h" + str(m) + "m" + str(s) + "s"


def link_time_to_timestamp(link_time):
    if "h" not in link_time:
        link_time = "0h" + link_time
    return link_time.replace("h", ":").replace("m", ":").replace("s", "")


def link_time_to_seconds(link_time):
    return get_seconds(link_time_to_timestamp(link_time))


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


def round_down(num, divisor):
    return num - (num % divisor)


def top_item(x):
    sorted_x = sorted(x.items(), key=lambda item: item[1], reverse=True)
    if not sorted_x:
        return "null", (-1, "")
    return sorted_x[0]


def total_value(d):
    v = 0
    for k in d:
        v += d[k][0]
    return v


def add_value(d, k, v0, v1):
    if k in d:
        d[k] = (d[k][0] + v0, d[k][1])
    else:
        d[k] = (v0, v1)


def space_timestamp(timestamp):
    return timestamp.replace("h", "h ").replace("m", "m ")


def timestamp_url(video_id, secs):
    url = "http://twitch.tv/videos/" + video_id + "?t=" + link_time(secs)
    return url


def filter_match(filter, string):
    if "\"" in filter:
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


def get_normal_name(emote):
    return html.unescape(next(exrex.generate(emote)))


def get_normal_names(emote):
    normal_names = []
    for gen in exrex.generate(emote):
        normal = html.unescape(gen)
        normal_names.append(normal)
    return normal_names


def apply_filter(filter, emotes, multi_emotes):
    matches = []
    for emote in emotes:
        names = get_emote_names(emote, multi_emotes)
        for name in names:
            if filter_match(filter, name):
                matches.append(emote)
                break
    return matches


def wrap_text(text):
    wrapped = ''
    i = 0
    for char in text:
        i += 1
        if i > 20:
            wrapped += '\n'
            i = 0
        wrapped += char

    return wrapped
