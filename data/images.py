import hashlib
import os
import warnings

from common import config

print("Importing grequests...")
warnings.filterwarnings("ignore")
import grequests as greq

batch_size, completed = 0, 0


def get_image_hash(name):
    return hashlib.md5(name.encode()).hexdigest()


def image_exists(emote_name):
    return os.path.isfile(get_path(emote_name))


def missing_emotes(chat_emotes):
    missing = []
    for emote in chat_emotes:
        url = chat_emotes[emote]
        if not image_exists(url):
            missing.append(url)
    return missing


def get_path(name):
    return config.images_dir + os.path.sep + get_image_hash(name) + ".gif"


def request_exception(request, exception):
    print("Problem: {}: {}".format(request.url, exception))


def get_images(urls):
    results = multi_request(urls)
    for idx, result in enumerate(results):
        with open(get_path(urls[idx]), 'wb') as f:
            f.write(result.content)


def new_batch(size):
    global batch_size
    global completed
    batch_size = size
    completed = 0


def result_status(r, *args, **kwargs):
    global batch_size
    global completed
    completed += 1
    #display.window.update_status("Downloading images: {}%".format(int(completed / batch_size * 100)))


def multi_request(urls):
    new_batch(len(urls))
    results = greq.map((greq.get(u, hooks=dict(response=result_status)) for u in urls),
                       exception_handler=request_exception, size=None)
    return results
