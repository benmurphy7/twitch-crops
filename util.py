import datetime
import html

import exrex


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
    timestamp = link_time
    timestamp = timestamp.replace("h",":").replace("m",":").replace("s","")
    return timestamp

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

def space_timestamp(timestamp):
    return timestamp.replace("h", "h ").replace("m", "m ")

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