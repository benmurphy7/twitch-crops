# Twitch Crops
Analyzing emote usage in Twitch stream recordings.

Work in progress...

The main idea of this project is to find segments of stream videos that evoked a strong reaction from the audience - quantified by the use of Twitch emotes. 
The starting point is to track and visualize emote usage over time. This data can then be used to automatically crop videos into a collection of shorter clips, highlighting periods of stronger engagement. 
This could become a useful tool for viewers, providing a way to watch the best moments from a longer broadcast without the employment of an editor.

-Built with [Python 3.8.6](https://www.python.org/downloads/release/python-386/) <br/>

## Setup:

Get  [Twitch client ID & client secret](https://dev.twitch.tv/console/apps) and create ```clientInfo.txt``` in base directory

```
clientInfo.txt:
<client_id>
<client_secret>
```


Run with ```python main.py```



## Using the UI:

Enter a stream video ID which will update the available emotes for that channel, and add optional filters.


Provide filters as a space-separated list of emote names. Use quotes for contains search.  
```Ex: "LUL" KEK = LUL, LULW, ... , KEK```

The resulting plot will show points which can be clicked to play the video from the timestamp (with a slight introduction)  

