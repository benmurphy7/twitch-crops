import gevent.monkey
gevent.monkey.patch_all()

import twitch
from flask import Flask, render_template, request
import ssl

from data import collect, logs, analyze
from common import util

# Flask constructor takes the name of
# current module (__name__) as argument.
app = Flask(__name__)


# The route() function of the Flask class is a decorator,
# which tells the application which URL should call
# the associated function.
@app.route('/', methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        print(request.form)
        video_id = util.parse_video_id(request.form['video_id'])
        print(video_id)
        return display_video_info(video_id)

    else:
        return render_template('index.html')


@app.route('/chart', methods=('GET', 'POST'))
def chart():
    if request.method == 'POST':
        print(request.form)
        video_id = util.parse_video_id(request.form['video_id'])
        print(video_id)
        render_chart(video_id)
    return render_template('chart.html')


def display_video_info(video_id):
    video_info = {}
    collect.update_video_info(video_id)
    video: twitch.Helix.video = collect.video_info

    video_info['title'] = video.title
    video_info['user_name'] = video.user_name
    video_info['duration'] = util.space_timestamp(video.duration)

    return render_template('video_analysis.html', video_info=video_info)


def render_chart(video_id, filter_list=[]):
    collect.update_video_info(video_id)
    chat_emotes = collect.get_available_emotes()
    data, valid, invalid, stats = logs.parse_vod_log(video_id, chat_emotes, filter_list, 5)
    if invalid is None:
        analyze.plot_video_data(collect.video_info, data, valid, stats, 50, 10, True)
    else:
       print("Error: ' {} ' is not a valid filter".format(invalid))


if __name__ == '__main__':
    collect.client = collect.initialize_client()
    # run() method of Flask class runs the application
    # on the local development server.
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.verify_mode = ssl.CERT_REQUIRED
    #context.load_verify_locations("ca.crt")
    context = ('twitchcrops_tv.crt', 'twitchcrops_tv.key')  # certificate and key files
    app.run(host='0.0.0.0', port=443, ssl_context=context)