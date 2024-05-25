# -*- coding: utf-8 -*-
# AltStore-Proxy
# Project by https://github.com/rix1337

import json

import requests


def readable_size(size):
    if size:  # integer byte value
        power = 2 ** 10
        n = 0
        powers = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        size = round(size, 2)
        size = str(size) + " " + powers[n] + 'B'
        return size
    else:
        return ""


def discord_webhook(shared_state, app):
    webhook_url = shared_state.values["discord_webhook"]

    headers = {
        'User-Agent': 'AltStore-Proxy',
        'Content-Type': 'application/json'
    }

    if app['versionDescription']:
        description = app['versionDescription']
    else:
        description = app['localizedDescription']

    data = {
        'username': 'AltStore-Proxy',
        'avatar_url': 'https://altstore.io/images/AltStore_AppIcon.png',
        'embeds': [{
            'title': f"{app['name']} v.{app['version']}",
            'description': description,
            'thumbnail': {
                'url': app['iconURL']
            },
            'fields': [
                {
                    'name': "Size",
                    'value': readable_size(app['size']),
                }, {
                    'name': "Download",
                    'value': f'[{app["filename"]}]({app["downloadURL"]})'
                }

            ]
        }]
    }

    try:
        response = requests.post(webhook_url, data=json.dumps(data), headers=headers)
        if response.status_code == 204:
            print('Notification sent to Discord')
            return True
        else:
            print(f'ERROR - Could not send to Discord - {response.status_code}')
    except Exception as e:
        print(f'ERROR - Could not send to Discord - {str(e)}')
    return False
