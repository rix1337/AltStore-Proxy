#  AltStore-Proxy

[![PyPI version](https://badge.fury.io/py/altstore-proxy.svg)](https://badge.fury.io/py/altstore-proxy)
[![Github Sponsorship](https://img.shields.io/badge/support-me-red.svg)](https://github.com/users/rix1337/sponsorship)

A simple proxy for slow AltStore servers

# Setup

`pip install altstore_proxy`

# Run

```
altstore_proxy
  --port=8080
  --baseurl=https://example.com
  --cache=/tmp/altstore_cache
  --repos=https://fake.tld/apps.json,https://foo.bar/altstore.json
```

# Docker
```
docker run -d \
  --name="AltStore-Proxy" \
  -p port:8080 \
  -v /path/to/cache/:/cache:rw \
  -e 'BASEURL'='https://example.com'
  -e 'REPOS'='https://fake.tld/apps.json,https://foo.bar/altstore.json'
  rix1337/docker-altstore-proxy:latest
  ```
