# -*- coding: utf-8 -*-
# AltStore-Proxy
# Projekt by https://github.com/rix1337

import argparse
import sys
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler

import requests
from bottle import Bottle, abort

port = None
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Desired Port, defaults to 8080")
    arguments = parser.parse_args()

    global port

    if arguments.port:
        port = arguments.port
    else:
        port = 8080

    if port is None:
        print("[AltStore-Proxy] Error: No Port specified")
        sys.exit(1)

    print("[AltStore-Proxy] Version " + str(version))
    print("[AltStore-Proxy] Starting Webserver on Port " + str(port))

    app = Bottle()

    @app.get("/")
    def status():
        return "AltStore-Proxy is running!"

    @app.get("/status")
    def status():
        try:
            global active
            return str(active).lower()
        except Exception as e:
            print("[AntiGateHandler] status - Error: " + str(e))
        return abort(400, "Failed")

    @app.get("/do/<payload>")
    def to_decrypt(payload):
        global active
        global already_solved
        print(payload)
        requests.get("https://google.com")

    Server(app, listen='0.0.0.0', port=port).serve_forever()


if __name__ == "__main__":
    main()
