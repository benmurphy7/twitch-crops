import re

import requests as req
import twitch

chat_emotes = {}

def get_client_info(file):
    with open(file) as f:
        lines = f.readlines()
        return lines[0].strip(), lines[1].strip()

def add_emote(key, url):
    global chat_emotes
    if key not in chat_emotes:
        chat_emotes[key] = url
        return 1
    else:
        return 0

def get_value(key, str):
   return re.search('\'' + key + '\': \'(.*?)\',', str).group(1)

def get_emote_info(emote):
    return emote['code'], emote['id']

def add_bttv_emote(emote):
    bttv_url = "https://cdn.betterttv.net/emote/"
    name, id = get_emote_info(emote)
    url = bttv_url + str(id) + "/1x"
    return add_emote(name, url)

def add_ttv_emote(emote):
    ttv_url = "https://static-cdn.jtvnw.net/emoticons/v1/"
    name, id = get_emote_info(emote)
    url = ttv_url + str(id) + "/1.0"
    return add_emote(name, url)

def get_available_emotes(video_id):
    # --Supported emote sources--
    # TTV
    # BTTV
    # FFZ

    global chat_emotes
    chat_emotes = {}
    user_name = ""
    user_id = ""

    client_id, client_secret = get_client_info('./clientInfo.txt')
    client = twitch.Helix(client_id=client_id, client_secret=client_secret)

    try:
        for video in client.videos(video_id):
            user_name = video.user_name
            user_id = video.user_id
    except:
        return chat_emotes, user_id, user_name

    print("\nVideo title: " + video.title)
    print("Channel: " + user_name)

    bttv = 0
    ffz = 0
    ttv = 0

    #Get BTTV emotes
    try:
        bttv_user = req.get('https://api.betterttv.net/3/cached/users/twitch/' + user_id ).json()

        for emote in bttv_user['sharedEmotes']:
            bttv += add_bttv_emote(emote)

        for emote in bttv_user['channelEmotes']:
            bttv += add_bttv_emote(emote)

        bttv_global = req.get('https://api.betterttv.net/3/cached/emotes/global').json()

        for emote in bttv_global:
            bttv += add_bttv_emote(emote)
    except:
        print("Error loading BTTV emotes")
        pass

    #Get FFZ emotes
    try:
        ffz_room = req.get('https://api.frankerfacez.com/v1/room/id/' + user_id ).json()
        sets = ffz_room['sets']

        for set in sets:
            for emoticon in sets[set]['emoticons']:
                name = emoticon['name']
                url_dict = emoticon['urls']
                # Get highest resolution image available
                url = "https:" + url_dict[list(url_dict)[0]]
                ffz += add_emote(name, url)
    except:
        print("Error loading FFZ emotes")
        pass

    #Get global twitch emotes
    global_emotes = req.get('https://api.twitchemotes.com/api/v4/channels/0').json()
    for emote in global_emotes['emotes']:
        ttv += add_ttv_emote(emote)
        print(emote)

    #Get twitch channel emotes
    try:
        channel_emotes = req.get('https://api.twitchemotes.com/api/v4/channels/' + user_id ).json()
        for emote in channel_emotes['emotes']:
            ttv += add_ttv_emote(emote)
    except:
        print("Error loading Twitch channel emotes")

    print("\nFound {} available emotes:".format(len(chat_emotes)))
    print("\nTTV: {}\nBTTV: {}\nFFZ: {}\n".format(ttv, bttv, ffz))

    return chat_emotes, video.title, video.user_name





