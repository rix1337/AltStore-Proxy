# -*- coding: utf-8 -*-
# AltStore-Proxy
# Project by https://github.com/rix1337

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

from altstore_proxy.providers import shared_state, version


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

    filename = os.path.join(shared_state.values["cache"], os.path.basename(url))
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Check if file already exists and compare sizes
    if os.path.exists(filename):
        existing_file_size = os.path.getsize(filename)
        if existing_file_size == total_size_in_bytes:
            print(f"File {filename} already exists with the same size. Skipping download.")
            return filename

    print(f"Downloading {url} to {filename}")
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    with open(filename, 'wb') as f:
        for data in response.iter_content(chunk_size=1024):
            progress_bar.update(len(data))
            f.write(data)
    progress_bar.close()
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("ERROR, something went wrong")

    return filename


def update_json_proxy(shared_state_dict, shared_state_lock):
    shared_state.set_state(shared_state_dict, shared_state_lock)

    try:
        while True:
            print("[AltStore-Proxy] Updating cache...")

            merged_json = {
                "name": "AltStore-Proxy",
                "subtitle": "A simple proxy for slow AltStore servers.",
                "iconURL": "https://altstore.io/images/AltStore_AppIcon.png",
                "website": "https://github.com/rix1337/AltStore-Proxy",
                "apps": [],
                "news": []
            }

            for repo in shared_state.values["repos_to_cache"]:
                response = requests.get(repo)
                data = response.json()
                for app in data['apps']:
                    print("Found " + app['name'] + ", v." + app['version'])
                    download_url = app['downloadURL']
                    filename = download_and_cache_ipa(download_url)
                    if filename.startswith("/"):
                        filename = filename[1:]
                    app['downloadURL'] = shared_state.values["baseurl"] + '/' + filename
                merged_json['apps'].extend(data['apps'])

            shared_state.update("ready", True)
            shared_state.update("merged_json", merged_json)

            time.sleep(3600)
    except KeyboardInterrupt:
        sys.exit(0)


def main():
    with multiprocessing.Manager() as manager:
        shared_state_dict = manager.dict()
        shared_state_lock = manager.Lock()
        shared_state.set_state(shared_state_dict, shared_state_lock)

        print("[AltStore-Proxy] Version " + version.get_version() + " by rix1337")
        shared_state.update("ready", False)

        parser = argparse.ArgumentParser()
        parser.add_argument("--port", help="Desired Port, defaults to 8080")
        parser.add_argument("--baseurl", help="Base URL for the AltStore-Proxy (for reverse proxy usage)")
        parser.add_argument("--cache", help="Desired Cache Directory, defaults to ./cache")
        parser.add_argument("--repos", help="Desired apps.json Repositories to Cache - comma separated")
        arguments = parser.parse_args()

        if arguments.port:
            try:
                shared_state.update("port", int(arguments.port))
            except ValueError:
                print("[AltStore-Proxy] Port must be an integer")
                sys.exit(1)
        else:
            shared_state.update("port", 8080)

        if arguments.cache:
            shared_state.update("cache", arguments.cache)
        else:
            shared_state.update("cache", "./cache")

        if arguments.baseurl:
            shared_state.update("baseurl", arguments.baseurl)
        else:
            shared_state.update("baseurl", "http://127.0.0.1:" + str(shared_state.values["port"]))

        if shared_state.values["baseurl"][-1] == "/":
            shared_state.update("baseurl", shared_state.values["baseurl"][:-1])
        if not shared_state.values["baseurl"].startswith("http"):
            print("[AltStore-Proxy] Base URL must start with http:// or https://")
            sys.exit(1)
        if not shared_state.values["baseurl"]:
            print("[AltStore-Proxy] Base URL must not be empty")
            sys.exit(1)
        print("[AltStore-Proxy] Base URL: " + shared_state.values["baseurl"])

        try:
            os.makedirs(shared_state.values["cache"], exist_ok=True)
            print("[AltStore-Proxy] Cache directory: " + shared_state.values["cache"])
        except Exception as e:
            print("[AltStore-Proxy] Error creating cache directory: " + str(e))
            sys.exit(1)

        if arguments.repos:
            shared_state.update("repos_to_cache", arguments.repos.split(","))
            print("[AltStore-Proxy] Using custom repositories: " + str(shared_state.values["repos_to_cache"]))
        else:
            shared_state.update("repos_to_cache", [
                "https://raw.githubusercontent.com/arichornlover/arichornlover.github.io/main/apps.json",
                "https://raw.githubusercontent.com/lo-cafe/winston-altstore/main/apps.json"
            ])
            print("[AltStore-Proxy] No repositories provided, using default repositories: " + str(
                shared_state.values["repos_to_cache"]))

        app = Bottle()

        @app.get("/")
        def status():
            repos_html = ''.join(
                f'<li><a href="{repo}">{repo}</a></li>' for repo in shared_state.values["repos_to_cache"])
            return f'''
            <html>
            <head>
                <title>AltStore-Proxy</title>
                <style>
                    body {{
                        background: linear-gradient(to right, #f9f9f9, #e0e0e0);
                        font-family: Arial, sans-serif;
                        padding: 20px;
                        text-align: center;
                    }}
                    button {{
                        font-size: 20px;
                        padding: 10px 20px;
                        margin-top: 20px;
                        background-color: #4CAF50; /* Green */
                        border: none;
                        color: white;
                        text-align: center;
                        text-decoration: none;
                        display: inline-block;
                        font-size: 16px;
                        transition-duration: 0.4s;
                        cursor: pointer;
                    }}
                    button:hover {{
                        background-color: #45a049;
                    }}
                </style>
            </head>
            <body>
                <h1>AltStore-Proxy</h1>
                <a href="/apps.json">Source for use in AltStore</a><br>
                <a href="altstore://source?url={shared_state.values["baseurl"]}/apps.json">
                    <button>Add this source to AltStore to receive app updates</button>
                </a>
                <h2>Source Repositories</h2>
                <ul>
                    {repos_html}
                </ul>
            </body>
            </html>'''

        @app.get('/cache/<filename:path>')
        def serve_file(filename):
            return static_file(filename, root=shared_state.values["cache"], download=filename)

        @app.get("/apps.json")
        def status():
            try:
                return shared_state.values["merged_json"]
            except Exception as e:
                print("[AntiGateHandler] status - Error: " + str(e))
            return abort(503, "Cache not initialized. Please try again later.")

        hourly_update = multiprocessing.Process(target=update_json_proxy, args=(shared_state_dict, shared_state_lock,))
        hourly_update.start()

        while not shared_state.values["ready"]:
            time.sleep(1)

        print(
            "[AltStore-Proxy] Add this source to AltStore by opening " + shared_state.values[
                "baseurl"] + " on your mobile device.")
        try:
            Server(app, listen='0.0.0.0', port=shared_state.values["port"]).serve_forever()
        except KeyboardInterrupt:
            hourly_update.terminate()
            sys.exit(0)


if __name__ == "__main__":
    main()
