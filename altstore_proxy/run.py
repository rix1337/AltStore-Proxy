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

from altstore_proxy.providers import shared_state, version, notifications


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


def determine_file_name_from_stream(response):
    content_disposition = response.headers.get('content-disposition')
    if content_disposition:
        filename = content_disposition.split("filename=")[1]
        if filename:
            return filename
    return None


def download_and_cache_ipa(app):
    url = app['downloadURL']

    response = requests.get(url, stream=True, allow_redirects=True)
    total_size_in_bytes = int(response.headers.get('content-length', 0))

    if response.url != url:
        url = response.url
        response = requests.get(url, stream=True, allow_redirects=False)

    file_name = determine_file_name_from_stream(response)
    if not file_name:
        file_name = os.path.basename(url)
    if not file_name:
        file_name = f"{app['name']}_{app['version']}".translate(str.maketrans(" :/", "___"))
    if not file_name.endswith(".ipa"):
        file_name += ".ipa"

    file_path = os.path.join(shared_state.values["cache"], file_name)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Check if file already exists and compare sizes
    if os.path.exists(file_path):
        existing_file_size = os.path.getsize(file_path)
        if existing_file_size == total_size_in_bytes:
            print(f"File {file_path} already exists with the same size. Skipping download.")
            return file_name, True

    print(f"Downloading {url} to {file_path}")
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    with open(file_path, 'wb') as f:
        for data in response.iter_content(chunk_size=1024):
            progress_bar.update(len(data))
            f.write(data)
    progress_bar.close()
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("ERROR, something went wrong")

    return file_name, False


def cache_repositories(shared_state_dict, shared_state_lock):
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
                    app['filename'], skipped = download_and_cache_ipa(app)
                    app['downloadURL'] = shared_state.values["baseurl"] + '/cache/' + app['filename']

                    if not skipped:
                        if shared_state.values['discord_webhook']:
                            notifications.discord_webhook(shared_state, app)

                merged_json['apps'].extend(data['apps'])

            shared_state.update("merged_json", merged_json)

            print("[AltStore-Proxy] Cache updated. Next update in 1 hour.")
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
        parser.add_argument("--discord_webhook", help="Discord Webhook URL for notifications")
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

        if arguments.discord_webhook:
            shared_state.update("discord_webhook", arguments.discord_webhook)
            print("[AltStore-Proxy] Using Discord Webhook for update notifications")
        else:
            shared_state.update("discord_webhook", "")
            print("[AltStore-Proxy] No update notifications set up.")

        app = Bottle()

        @app.get("/")
        def status():
            try:
                app_links = ""
                for app in shared_state.values["merged_json"]['apps']:
                    app_links += f'<a href="{app["downloadURL"]}" class="button grey">{app["name"]}</a><br>'

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
                        .button {{
                            display: inline-block;
                            font-size: 16px;
                            margin: 10px;
                            padding: 10px 20px;
                            color: white;
                            text-decoration: none;
                            transition-duration: 0.4s;
                            cursor: pointer;
                            border-radius: 5px;
                        }}
                        .button.grey {{
                            background-color: #808080; /* Grey */
                        }}
                        .button.grey:hover {{
                            background-color: #696969; /* Darker Grey */
                        }}
                        .button.green {{
                            background-color: #4CAF50; /* Green */
                        }}
                        .button.green:hover {{
                            background-color: #45a049;
                        }}
                    </style>
                </head>
                <body>
                    <h1>AltStore-Proxy</h1>
                    {app_links}
                    <a href="altstore://source?url={shared_state.values["baseurl"]}/apps.json">
                        <button class="button green">Add this source to AltStore to receive app updates</button>
                    </a><br><br>
                    <a href="/apps.json">Source for use in AltStore</a>
                </body>
                </html>'''
            except Exception as e:
                print("[AntiGateHandler] status - Error: " + str(e))
            return abort(503, "Cache not initialized. Please try again later.")

        @app.get('/cache/<filename:path>')
        def serve_file(filename):
            return static_file(filename, root=shared_state.values["cache"], download=filename,
                               mimetype='application/octet-stream')

        @app.get("/apps.json")
        def status():
            try:
                return shared_state.values["merged_json"]
            except Exception as e:
                print("[AntiGateHandler] status - Error: " + str(e))
            return abort(503, "Cache not initialized. Please try again later.")

        hourly_update = multiprocessing.Process(target=cache_repositories, args=(shared_state_dict, shared_state_lock,))
        hourly_update.start()

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
