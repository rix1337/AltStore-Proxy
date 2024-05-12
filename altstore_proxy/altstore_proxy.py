# -*- coding: utf-8 -*-
# AltStore-Proxy
# Projekt by https://github.com/rix1337

import argparse
import multiprocessing
import os
import sys
import time
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler

import requests
from bottle import Bottle, abort, static_file
from tqdm import tqdm

from altstore_proxy.providers import shared_state

version = "0.0.1"


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


class Server:
    def __init__(self, wsgi_app, listen='127.0.0.1', port=8080):
        self.wsgi_app = wsgi_app
        self.listen = listen
        self.port = port
        self.server = make_server(self.listen, self.port, self.wsgi_app,
                                  ThreadingWSGIServer, handler_class=NoLoggingWSGIRequestHandler)

    def serve_forever(self):
        self.server.serve_forever()


def download_and_cache_ipa(url):
    response = requests.get(url, stream=True, allow_redirects=True)
    total_size_in_bytes = int(response.headers.get('content-length', 0))

    # Resolve the actual URL if the provided URL is a shortened URL
    if "tinyurl.com" in url:
        url = response.url

    filename = os.path.join('cache', os.path.basename(url))

    print(f"Downloading {url} to {filename}")
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Check if file already exists and compare sizes
    if os.path.exists(filename):
        existing_file_size = os.path.getsize(filename)
        if existing_file_size == total_size_in_bytes:
            print(f"File {filename} already exists with the same size. Skipping download.")
            return filename

    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    with open(filename, 'wb') as f:
        for data in response.iter_content(chunk_size=1024):
            progress_bar.update(len(data))
            f.write(data)
    progress_bar.close()
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("ERROR, something went wrong")

    return filename


def merge_jsons(shared_state_dict, shared_state_lock):
    shared_state.set_state(shared_state_dict, shared_state_lock)

    try:
        while True:
            merged_json = {
                "apps": []
            }

            for repo in shared_state.values["repos_to_cache"]:
                response = requests.get(repo)
                data = response.json()
                for app in data['apps']:
                    print("Found " + app['name'] + ", v." + app['version'])
                    download_url = app['downloadURL']
                    filename = download_and_cache_ipa(download_url)
                    app['downloadURL'] = 'http://127.0.0.1:' + str(shared_state.values["port"]) + '/' + filename
                merged_json['apps'].extend(data['apps'])

            shared_state.update("merged_json", merged_json)

            time.sleep(3600)
    except KeyboardInterrupt:
        sys.exit(0)


def main():
    with multiprocessing.Manager() as manager:
        shared_state_dict = manager.dict()
        shared_state_lock = manager.Lock()
        shared_state.set_state(shared_state_dict, shared_state_lock)

        parser = argparse.ArgumentParser()
        # ToDo add argument for custom cache directory
        # ToDo add argument for custom repos
        # ToDo add argument for custom base url (in case of proxy / nonlocal usage)
        parser.add_argument("--port", help="Desired Port, defaults to 8080")
        arguments = parser.parse_args()

        if arguments.port:
            shared_state.update("port", arguments.port)
        else:
            shared_state.update("port", 8080)

        shared_state.update("repos_to_cache", [
            "https://raw.githubusercontent.com/arichornlover/arichornlover.github.io/main/apps.json",
            "https://raw.githubusercontent.com/lo-cafe/winston-altstore/main/apps.json"
        ])

        print("[AltStore-Proxy] Version " + str(version))

        app = Bottle()

        @app.get("/")
        def status():
            return "AltStore-Proxy is running! Add this URL + /apps.json to your AltStore."

        @app.get('/cache/<filename:path>')
        def serve_file(filename):
            return static_file(filename, root='cache', download=filename)

        @app.get("/apps.json")
        def status():
            try:
                return shared_state.values["merged_json"]
            except Exception as e:
                print("[AntiGateHandler] status - Error: " + str(e))
            return abort(503, "Cache not initialized. Please try again later.")

        hourly_update = multiprocessing.Process(target=merge_jsons, args=(shared_state_dict, shared_state_lock,))
        hourly_update.start()

        print(
            "[AltStore-Proxy] AltStores proxied at http://127.0.0.1:" + str(shared_state.values["port"]) + "/apps.json")
        try:
            Server(app, listen='0.0.0.0', port=shared_state.values["port"]).serve_forever()
        except KeyboardInterrupt:
            hourly_update.terminate()
            sys.exit(0)


if __name__ == "__main__":
    main()
