#  AltStore-Proxy

[![PyPI version](https://badge.fury.io/py/altstore-proxy.svg)](https://badge.fury.io/py/altstore-proxy)
[![Github Sponsorship](https://img.shields.io/badge/support-me-red.svg)](https://github.com/users/rix1337/sponsorship)

A simple proxy for slow AltStore servers.

# Run
```
docker run -d \
  --name="AltStore-Proxy" \
  -p port:8080 \
  -v /path/to/cache/:/cache:rw \
  rix1337/docker-altstore-proxy
  ```
  
# Optional Parameters
 - `-e BASEURL` Base URL for the AltStore-Proxy (for reverse proxy usage)
 - `-e REPOS` Desired apps.json Repositories to Cache - comma separated
