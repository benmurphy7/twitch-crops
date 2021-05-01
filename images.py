import hashlib
import os

import gevent.monkey

gevent.monkey.patch_all()

import grequests as greq

import main


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
    return main.images_dir + os.path.sep + get_image_hash(name) + ".gif"


def request_exception(request, exception):
    print("Problem: {}: {}".format(request.url, exception))


def get_images(urls):
    results = multi_request(urls)
    for idx, result in enumerate(results):
        with open(get_path(urls[idx]), 'wb') as f:
            f.write(result.content)


def multi_request(urls):
    results = greq.map((greq.get(u) for u in urls), exception_handler=request_exception, size=None)
    return results
