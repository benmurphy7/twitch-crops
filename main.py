import tcd
import os
from os import path
import datetime
import operator
import matplotlib.pylab as plt

def toTimestamp(secs):
    return str(datetime.timedelta(seconds=secs))

def getSeconds(timestamp):
    h, m, s = timestamp.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

def getTimestamp(line):
    endIdx = line.find("]")
    timestamp = line[1:endIdx]
    return timestamp

def parse(logPath, emotes):
    times = {}
    with open(logPath) as f:
        f = f.readlines()

    for line in f:
        for emote in emotes:
            if emote in line:
                timestamp = getTimestamp(line)
                seconds = timestamp#getSeconds(timestamp)
                #print("{} = {} seconds = {}".format(timestamp, seconds, toTimestamp(seconds)))
                if seconds in times:
                    times[seconds] += 1
                else:
                    times[seconds] = 1

    #print(toTimestamp(max(times.items(), key=operator.itemgetter(1))[0]))
    plotDict(times)
def plotDict(dict):
    lists = sorted(dict.items())  # sorted by key, return a list of tuples

    x, y = zip(*lists)  # unpack a list of pairs into two tuples

    plt.plot(x, y)
    plt.show()


#-------------------------------
#            Main
#-------------------------------
# "~" doesnt work, use the absolute path
downloadDir = "/home/ben/Projects/TwitchCrops/Downloads"
videoID = "877276526"
logPath = downloadDir + "/{}.log".format(videoID)

if not path.exists(logPath):
    print("File not found. Downloading...")
    os.system("tcd --video {} --format irc --output {}".format(videoID,downloadDir))
else:
    print("Log already exists")

emoteList = []

emoteList.append("LUL")

times = parse(logPath, emoteList)

#Get a list of emotes (Store in hash table?)
#Parse all messages and check emote table
#Save all emote timestamps? - need to cluster, potentially with multiple emotes
#Profile - select sets of emotes to cluster (or find associations via analysis)


