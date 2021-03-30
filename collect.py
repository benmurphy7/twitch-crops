import re

import gevent.monkey
gevent.monkey.patch_all()

import requests as req
import twitch

import main

chat_emotes = {}
client = None #twitch.Helix()
video_info: None #twitch.Helix.video()

rechat_url = "https://rechat.twitch.tv/rechat-messages"

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

def initialize_client():
    client_id, client_secret = get_client_info(main.client_info)
    return twitch.Helix(client_id=client_id, client_secret=client_secret)

def update_video_info(video_id):
    global video_info
    try:
        for video in client.videos(video_id):
            video_info = video
    except Exception as e:
        return False
    return True

def get_available_emotes():
    # --Supported emote sources--
    # TTV
    # BTTV
    # FFZ

    global chat_emotes
    global video_info
    global client
    chat_emotes = {}

    #if not update_video_info(video_id):
        #return chat_emotes, None, None

    print("\nVideo title: " + video_info.title)
    print("Channel: " + video_info.user_name)

    bttv = 0
    ffz = 0
    ttv = 0

    #Get BTTV emotes
    try:
        bttv_user = req.get('https://api.betterttv.net/3/cached/users/twitch/' + video_info.user_id ).json()

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
        ffz_room = req.get('https://api.frankerfacez.com/v1/room/id/' + video_info.user_id ).json()
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

    #Get twitch channel emotes
    try:
        channel_emotes = req.get('https://api.twitchemotes.com/api/v4/channels/' + video_info.user_id ).json()
        for emote in channel_emotes['emotes']:
            ttv += add_ttv_emote(emote)
    except:
        print("Error loading Twitch channel emotes")

    print("\nFound {} available emotes:".format(len(chat_emotes)))
    print("\nTTV: {}\nBTTV: {}\nFFZ: {}\n".format(ttv, bttv, ffz))

    return chat_emotes


#TESTING


"""
Hook for grequest responses (use to track total progress of large batch)

def request_fulfilled(r, *args, **kwargs):
    track_requests.update()

local_path = 'https://www.google.com/search?q={}'
parameters = [('the+answer+to+life+the+universe+and+everything'), ('askew'), ('fun+facts')]
    global track_requests # missing this line was the cause of my issue...
    s = requests.Session()
    s.hooks['response'].append(request_fulfilled) # assign hook here
    retries = Retry(total=5, backoff_factor=0.2, status_forcelist=[500,502,503,504], raise_on_redirect=True, raise_on_status=True)
    s.mount('http://', HTTPAdapter(max_retries=retries))
    s.mount('https://', HTTPAdapter(max_retries=retries))
    async_list = []
    for parameters in parameter_list:
        URL = local_path.format(*parameters)
        async_list.append(grequests.get(URL, session=s))
    track_requests = tqdm(total=len(async_list))
    results = grequests.map(async_list)
    track_requests.close()
    track_requests = None

"""



