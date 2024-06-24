FROM alpine:latest
MAINTAINER rix1337

# Define package name
ARG PACKAGE_NAME=altstore-proxy

# build tools
RUN apk add --no-cache curl build-base jq python3-dev py3-pip

# Optionally set desired version for the build
ARG VS="false"
RUN echo "VS: ${VS}"

# setup
RUN pip3 install --upgrade pip \
  && pip3 install wheel

# Install specified package version and clean up unneeded packages
RUN if [[ ${VS} == "false" ]] ; then echo "Grabbing latest version from pypi.org" && VERSION=$(curl -Ls https://pypi.org/pypi/${PACKAGE_NAME}/json | jq -r .info.version) ; else echo "Using version from workflow_dispatch input" && VERSION=$VS ; fi  && \
  echo $VERSION && \
  pip3 install ${PACKAGE_NAME}=="$VERSION" --no-cache-dir && \
    apk del curl build-base jq

# volumes and ports
VOLUME /cache
EXPOSE 8080
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["sh", "-c", "altstore_proxy --port=8080 --cache=/cache --baseurl=$BASEURL --repos=$REPOS --discord_webhook=$DISCORD_WEBHOOK"]
