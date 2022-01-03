import re
import traceback

from common import config

print("Importing requests...")
import requests as req
import twitch

#TODO: Store data in object
client: twitch.Helix = None

def get_client_info(file):
    with open(file) as f:
        lines = f.readlines()
        return lines[0].strip(), lines[1].strip()


def add_emote(chat_emotes, key, url):
    if "-" in key:
        return 0
    if key not in chat_emotes:
        chat_emotes[key] = url
        return 1
    else:
        return 0


def get_value(key, str):
    return re.search('\'' + key + '\': \'(.*?)\',', str).group(1)


def get_emote_info(emote):
    string = ""
    if 'name' in emote:
        string = emote['name']
    elif 'code' in emote:
        string = emote['code']

    return string, emote['id']


def add_bttv_emote(chat_emotes, emote):
    bttv_url = "https://cdn.betterttv.net/emote/"
    name, id = get_emote_info(emote)
    url = bttv_url + str(id) + "/1x"
    return add_emote(chat_emotes, name, url)


def add_ttv_emote(chat_emotes, emote):
    ttv_url = "https://static-cdn.jtvnw.net/emoticons/v1/"
    name, id = get_emote_info(emote)
    url = ttv_url + str(id) + "/1.0"
    return add_emote(chat_emotes, name, url)


def initialize_client():
    client_id, client_secret = get_client_info(config.client_info)
    return twitch.Helix(client_id=client_id, client_secret=client_secret)

def get_video_info(video_id):
    video_info = None

    try:
        for video in client.videos(video_id):
            video_info = video
    except Exception as e:
        print(e)
        print(traceback.format_exc())
    return video_info

def update_video_info(video_id):
    global video_info

    try:
        for video in client.videos(video_id):
            video_info = video
    except Exception as e:
        print(traceback.format_exc())
        return False
    return True


def get_available_emotes(video: twitch.Helix.video):
    global client
    chat_emotes = {}

    print("video: {}".format(video))

    print('-'*80)
    print("\nVideo title: " + video.title)
    print("Channel: " + video.user_name)

    # --Supported emote sources--
    # TTV
    # BTTV
    # FFZ

    bttv, ffz, ttv = 0, 0, 0

    # Get BTTV emotes
    try:
        bttv_user = req.get('https://api.betterttv.net/3/cached/users/twitch/' + video.user_id).json()

        for emote in bttv_user['sharedEmotes']:
            bttv += add_bttv_emote(chat_emotes, emote)

        for emote in bttv_user['channelEmotes']:
            bttv += add_bttv_emote(chat_emotes, emote)

        bttv_global = req.get('https://api.betterttv.net/3/cached/emotes/global').json()

        for emote in bttv_global:
            bttv += add_bttv_emote(chat_emotes, emote)
    except:
        print("Error loading BTTV emotes")

    # Get FFZ emotes
    try:
        ffz_room = req.get('https://api.frankerfacez.com/v1/room/id/' + video.user_id).json()
        sets = ffz_room['sets']

        for set in sets:
            for emoticon in sets[set]['emoticons']:
                name = emoticon['name']
                url_dict = emoticon['urls']
                url = "https:" + url_dict[list(url_dict)[0]]
                ffz += add_emote(chat_emotes, name, url)
    except:
        print("Error loading FFZ emotes")

    # Get global twitch emotes
    try:
        global_emotes = client.api.get('chat/emotes/global')
        for emote in global_emotes['data']:
            ttv += add_ttv_emote(chat_emotes, emote)
    except:
        print("Error loading Twitch global emotes")

    # Get twitch channel emotes
    try:
        channel_emotes = client.api.get('chat/emotes', params={'broadcaster_id': video.user_id})
        for emote in channel_emotes['data']:
            ttv += add_ttv_emote(chat_emotes, emote)
    except:
        print("Error loading Twitch channel emotes")

    print("\nFound {} available emotes:".format(len(chat_emotes)))
    print("\nTTV: {}\nBTTV: {}\nFFZ: {}\n".format(ttv, bttv, ffz))

    return chat_emotes
