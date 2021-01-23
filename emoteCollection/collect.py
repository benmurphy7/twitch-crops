import requests as req
import twitch
import re

def getClientInfo(file):
    with open(file) as f:
        lines = f.readlines()
        return lines[0].strip(), lines[1].strip()

def addEmote(key):
    global chat_emotes
    if key not in chat_emotes:
        chat_emotes[key] = 0
        return 1
    else:
        return 0

def getValue(key, str):
   return re.search('\'' + key + '\': \'(.*?)\',', str).group(1)

#--Supported emote sources--
#TTV
#BTTV
#FFZ

video_id = '882407401'
client_info = '../clientInfo.txt'
client_id, client_secret = getClientInfo(client_info)

chat_emotes = {}

client = twitch.Helix(client_id=client_id, client_secret=client_secret)

user_name = ""
user_id = ""

for video in client.videos(video_id):
    user_name = video.user_name
    user_id = video.user_id

print("\nGetting emotes for channel: " + user_name)

bttv = 0
ffz = 0
ttv = 0

#Get BTTV emotes
try:
    bttv_user = req.get('https://api.betterttv.net/3/cached/users/twitch/' + user_id ).json()

    for emote in bttv_user['sharedEmotes']:
        bttv += addEmote(emote['code'])

    for emote in bttv_user['channelEmotes']:
        bttv += addEmote(emote['code'])

    bttv_global = req.get('https://api.betterttv.net/3/cached/emotes/global').json()

    for emote in bttv_global:
        bttv += addEmote(emote['code'])
except:
    print("Error loading BTTV emotes")
    pass

#Get FFZ emotes
try:
    ffz_room = req.get('https://api.frankerfacez.com/v1/room/id/' + user_id ).json()
    sets = ffz_room['sets']

    for set in sets:
        for emoticon in sets[set]['emoticons']:
            name = getValue('name', str(emoticon))
            ffz += addEmote(name)
except:
    print("Error loading FFZ emotes")
    pass

#Get global twitch emotes
global_emotes = req.get('https://api.twitchemotes.com/api/v4/channels/0').json()
for emote in global_emotes['emotes']:
    ttv += addEmote(emote['code'])

#Get twitch channel emotes
try:
    channel_emotes = req.get('https://api.twitchemotes.com/api/v4/channels/' + user_id ).json()
    for emote in channel_emotes['emotes']:
        ttv += addEmote(emote['code'])
except:
    print("Error loading Twitch channel emotes")

print("\nFound {} emotes:".format(len(chat_emotes)))
print("\nTTV: {}\nBTTV: {}\nFFZ: {}\n".format(ttv, bttv, ffz))







