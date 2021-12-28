import gevent.monkey

gevent.monkey.patch_all()

import twitch
from flask import Flask, render_template, request, render_template_string
import ssl

from data import collect, logs, analyze, images
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
        # request.args.get('a', 0, type=int)
        video_id = util.parse_video_id(request.form['video_id'])
        return display_video_info(video_id)

    else:
        return render_template('index.html')


@app.route('/submit', methods=('GET', 'POST'))
def submit():
    if request.method == 'POST':
        video_id = util.parse_video_id(request.form['video_id'])
        valid_id = collect.update_video_info(video_id)
        video: twitch.Helix.video = collect.video_info

        if not video_id or not valid_id:
            print('Inavlid Video ID')
            return

        video_info = {
            'id': video_id,
            'title': video.title,
            'user_name': video.user_name,
            'duration': util.space_timestamp(video.duration)
        }

        return render_template('video_analysis.html', video_info=video_info)


@app.route('/chart/<video_id>', methods=('GET', 'POST'))
def chart(video_id):
    valid_id = collect.update_video_info(video_id)
    video: twitch.Helix.video = collect.video_info

    if not video_id or not valid_id:
        print('Inavlid Video ID')
        return

    video_info = {
        'id': video_id,
        'title': video.title,
        'user_name': video.user_name,
        'duration': util.space_timestamp(video.duration)
    }

    style_str = "<style>h2 {text-align: center;}</style>"
    chart_title = "<h2>{} - {}</h2>".format(video.user_name, video.title)

    chart_html_str = render_chart(video_id)
    chart_html_str = style_str + chart_title + chart_html_str

    # return render_template('chart_view.html', video_info=video_info)
    return render_template_string(chart_html_str, video_info=video_info)


def display_video_info(video_id):
    video_info = {}
    valid_id = collect.update_video_info(video_id)
    video: twitch.Helix.video = collect.video_info

    if not video_id or not valid_id:
        print('Inavlid Video ID')
        return

    video_info['title'] = video.title
    video_info['user_name'] = video.user_name
    video_info['duration'] = util.space_timestamp(video.duration)

    return render_template('video_analysis.html', video_info=video_info)


def display_emotes(video_id):
    chat_emotes = collect.get_available_emotes()

    if chat_emotes is None:
        print('Inavlid Video ID')
        return

    urls = images.missing_emotes(chat_emotes)

    try:
        if urls:
            # self.update_status("Downloading images ...")
            images.get_images(urls)
    except Exception as e:
        print(e)


def render_chart(video_id, filter_list=[]):
    html_str = ""
    collect.update_video_info(video_id)
    chat_emotes = collect.get_available_emotes()
    data, valid, invalid, stats = logs.parse_vod_log(video_id, chat_emotes, filter_list, 5)
    if invalid is None:
        html_str = analyze.plot_video_data(collect.video_info, data, valid, stats, 50, 10, True)
    else:
        print("Error: ' {} ' is not a valid filter".format(invalid))

    return html_str


if __name__ == '__main__':
    collect.client = collect.initialize_client()
    # run() method of Flask class runs the application
    # on the local development server.
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.verify_mode = ssl.CERT_REQUIRED
    # context.load_verify_locations("ca.crt")
    context = ('twitchcrops_tv.crt', 'twitchcrops_tv.key')  # certificate and key files
    app.run(host='0.0.0.0', port=443, ssl_context=context)
