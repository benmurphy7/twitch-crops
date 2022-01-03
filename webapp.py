import subprocess
import traceback
import webbrowser
from datetime import datetime

import flask
import gevent.monkey
from jinja2 import Environment, FileSystemLoader
from markupsafe import escape
from werkzeug.utils import redirect

from common.util import get_filter_list

gevent.monkey.patch_all()

import twitch
from flask import Flask, render_template, request, render_template_string, url_for
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
        video_id = util.parse_video_id(request.form['video_id'])
        return display_video_info(video_id)
    else:
        return render_template('index.html', video_info=None)


@app.route('/info', methods=('GET', 'POST'))
def parse_info():
    if request.method == 'POST':
        video_id = request.form.get('video_id', default=None, type=None)
        if video_id:
            video_id = util.parse_video_id(video_id)
            return redirect(url_for('info', video_id=video_id))
        else:
            return render_template('index.html', video_info=None)


@app.route('/info/<video_id>', methods=('GET', 'POST'))
def info(video_id):
    video: twitch.Helix.video = collect.get_video_info(video_id)
    if not video_id or not video:
        return render_template(
            'index.html',
            video_info=None,
            id_msg="Error: '{}' is not a valid ID!".format(video_id))

    button_name = "Download"
    if logs.chat_log_exists(video_id):
        button_name = "Analyze"

    # Converts ISO date to human-readable string
    video_date = datetime.fromisoformat(str(video.created_at).replace('Z', '+00:00')).strftime('%B %d, %Y')

    video_info = {
        'id': video_id,
        'title': video.title,
        'user_name': video.user_name,
        'date': video_date,
        'duration': util.space_timestamp(video.duration)
    }

    return render_template('video_analysis.html', video_info=video_info, button_name=button_name)


@app.route('/download/<video_id>', methods=('GET', 'POST'))
def download(video_id):
    video: twitch.Helix.video = collect.get_video_info(video_id)
    if not video_id or not video:
        print('Inavlid Video ID')
        return

    # Converts ISO date to human-readable string
    video_date = datetime.fromisoformat(str(video.created_at).replace('Z', '+00:00')).strftime('%B %d, %Y')

    video_info = {
        'id': video_id,
        'title': video.title,
        'user_name': video.user_name,
        'date': video_date,
        'duration': util.space_timestamp(video.duration)
    }

    filters = request.args.get('filters', default='', type=None)

    def download_status():
        print('opening process')
        proc = subprocess.Popen(['node', 'download.js', video_id],
                                shell=True,
                                stdout=subprocess.PIPE
                                )
        while proc.poll() is None:
            print(proc.stdout.readline())
            yield proc.stdout.readline() #+ '<br/>\n'

    #env = Environment(loader=FileSystemLoader('templates'))
    #tmpl = env.get_template('video_analysis.html')
    #return flask.Response(render_template('video_analysis.html', video_info=video_info, filters=filters, download_status=download_status()))
    return flask.Response(download_status(),
                          mimetype='text/html')  # text/html is required for most browsers to show the partial page immediately

@app.route('/validate/<video_id>', methods=('GET', 'POST'))
def validate(video_id):
    video: twitch.Helix.video = collect.get_video_info(video_id)
    if not video_id or not video:
        print('Inavlid Video ID')
        return

    if not logs.chat_log_exists(video_id):
        return redirect(url_for('download', video_id=video_id))

    # Converts ISO date to human-readable string
    video_date = datetime.fromisoformat(str(video.created_at).replace('Z', '+00:00')).strftime('%B %d, %Y')

    video_info = {
        'id': video_id,
        'title': video.title,
        'user_name': video.user_name,
        'date': video_date,
        'duration': util.space_timestamp(video.duration)
    }

    filters = request.args.get('filters', default='', type=None)
    filter_list = get_filter_list(filters)

    valid, msg = validate_filters(video, filter_list)

    button_name = "Download"
    if logs.chat_log_exists(video_id):
        button_name = "Analyze"

    if valid:
        webbrowser.open_new_tab(url_for('chart', video_id=video_id, filters=filters, _external=True))

    return render_template('video_analysis.html', video_info=video_info, filters=filters, filter_msg=msg, button_name=button_name)


@app.route('/chart/<video_id>', methods=('GET', 'POST'))
def chart(video_id):
    video: twitch.Helix.video = collect.get_video_info(video_id)
    if not video_id or not video:
        print('Inavlid Video ID')
        return

    video_info = {
        'id': video_id,
        'title': video.title,
        'user_name': video.user_name,
        'duration': util.space_timestamp(video.duration)
    }

    filters = request.args.get('filters', default='', type=None)
    filter_list = get_filter_list(filters)

    title_str = '<title>{}</title>'.format(video.title)
    zoom_str = '<body onload="document.body.style.zoom = 1.25"> </body>'
    style_str = "<style>h2 {text-align: center;}</style>"
    chart_title = "<h2>{} - {}</h2>".format(video.user_name, video.title)

    render_str, code = render_chart(video, filter_list)

    if code != 0:
        return render_template('video_analysis.html', video_info=video_info, filters=filters, filter_msg=render_str)

    # TODO:
    # Show error message as HTML in chart page
    #   OR
    # Verify query strings (in a .../validate/... route and open new tab to redirected route if valid
    #   If NOT valid, need to show status as text via AJAX (jquery?)

    chart_html_str = title_str + zoom_str + style_str + chart_title + render_str

    # return render_template('chart_view.html', video_info=video_info)
    return render_template_string(chart_html_str, video_info=video_info)


def display_video_info(video_id):
    video: twitch.Helix.video = collect.get_video_info(video_id)
    if not video_id or not video:
        print('Inavlid Video ID')
        return

    video_info = {
        'id': video_id,
        'title': video.title,
        'user_name': video.user_name,
        'duration': util.space_timestamp(video.duration)
    }

    return render_template('video_analysis.html', video_info=video_info)


def display_emotes(video: twitch.Helix.video):
    chat_emotes = collect.get_available_emotes(video)

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
        print(traceback.format_exc())


def validate_filters(video: twitch.Helix.video, filter_list):
    chat_emotes = collect.get_available_emotes(video)

    for filter in filter_list:
        valid = False
        for emote in chat_emotes:
            if util.filter_match(filter, emote):
                valid = True
                break
        if not valid:
            return False, "Error: ' {} ' is not a valid filter!".format(filter)

    return True, ""


def render_chart(video: twitch.Helix.video, filter_list=[]):
    chat_emotes = collect.get_available_emotes(video)
    data, valid, invalid, stats = logs.parse_vod_log(video.id, chat_emotes, filter_list, 5)
    if invalid is None:
        html_str = analyze.plot_video_data(video, data, valid, stats, 50, 10, True)
    else:
        return "Error: ' {} ' is not a valid filter!".format(invalid), 1

    return html_str, 0


if __name__ == '__main__':
    collect.client = collect.initialize_client()
    # run() method of Flask class runs the application
    # on the local development server.
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.verify_mode = ssl.CERT_REQUIRED
    # context.load_verify_locations("ca.crt")
    context = ('twitchcrops_tv.crt', 'twitchcrops_tv.key')  # certificate and key files
    app.run(host='0.0.0.0', port=443, ssl_context=context)
