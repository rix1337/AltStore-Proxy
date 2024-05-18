FROM ghcr.io/linuxserver/baseimage-alpine:3.18
MAINTAINER rix1337

# build tools
RUN apk add --no-cache build-base python3-dev py3-pip

# Optionally set desired version for the build
ARG VS="false"
RUN echo "VS: ${VS}"

# setup
RUN pip3 install --upgrade pip \
  && pip3 install wheel

# Install specific version of FeedCrawler and clean up unneeded packages
RUN if [[ ${VS} == "false" ]] ; then echo "Grabbing latest altstore-proxy version from pypi.org" && VERSION=$(curl -Ls https://pypi.org/pypi/altstore-proxy/json | jq -r .info.version) ; else echo "Using version from workflow_dispatch input" && VERSION=$VS ; fi  && \
  echo $VERSION && \
  pip3 install altstore-proxy=="$VERSION" --no-cache-dir && \
    apk del build-base jq
  
# add local files
COPY root/ /

# volumes and ports
VOLUME /cache
EXPOSE 8080
ENV PYTHONUNBUFFERED=1
