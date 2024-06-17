# AltStore-Proxy

[![PyPI version](https://badge.fury.io/py/altstore-proxy.svg)](https://badge.fury.io/py/altstore-proxy)
[![Github Sponsorship](https://img.shields.io/badge/support-me-red.svg)](https://github.com/users/rix1337/sponsorship)

A simple proxy for slow AltStore servers

# Features

- Meant for use as custom Repo with AltStore Beta to facilitate faster downloading of apps
- Useful for manual app sideloading with AltStore (non-Beta), if used with Discord Webhook for update notifications

# Setup

`pip install altstore_proxy`

# Run

```
altstore_proxy
  --port=8080
  --baseurl=https://example.com
  --cache=/tmp/altstore_cache
  --repos=https://fake.tld/apps.json,https://foo.bar/altstore.json
  --discord_webhook=https://discord.com/api/webhooks/foo/bar
```

# Docker

```
docker run -d \
  --name="AltStore-Proxy" \
  -p port:8080 \
  -v /path/to/cache/:/cache:rw \
  -e 'BASEURL'='https://example.com'
  -e 'REPOS'='https://fake.tld/apps.json,https://foo.bar/altstore.json'
  -e 'DISCORD_WEBHOOK'='https://discord.com/api/webhooks/foo/bar'
  rix1337/docker-altstore-proxy:latest
  ```
