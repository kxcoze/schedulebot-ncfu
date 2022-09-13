# Separate build image
FROM python:3.9-slim-buster as compile-image
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# Final image
FROM python:3.9-slim-buster
COPY --from=compile-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /ncfubot
COPY app /ncfubot/app

# Change time
RUN apt-get install -y tzdata
ENV TZ=Europe/Moscow

# Install ru locale
RUN apt update && apt install -y --no-install-recommends locales; rm -rf /var/lib/apt/lists/*; sed -i '/^#.* ru_RU.UTF-8 /s/^#//' /etc/locale.gen; locale-gen

ENV DEBIAN_FRONTEND noninteractive
ENV GECKODRIVER_VER v0.29.0
ENV FIREFOX_VER 87.0

RUN set -x apt install -y firefox-esr && apt-get update && apt-get install -y curl
RUN apt-get update && apt-get install -y wget bzip2 libxtst6 libgtk-3-0 libx11-xcb-dev libdbus-glib-1-2 libxt6 libpci-dev && rm -rf /var/lib/apt/lists/*
# Add latest FireFox
RUN set -x \
   && apt update \
   && apt install -y \
       libx11-xcb-dev \
       libdbus-glib-1-dev \
   && curl -sSLO https://download-installer.cdn.mozilla.net/pub/firefox/releases/${FIREFOX_VER}/linux-x86_64/en-US/firefox-${FIREFOX_VER}.tar.bz2 \
   && tar -jxf firefox-* \
   && mv firefox /opt/ \
   && chmod 755 /opt/firefox \
   && chmod 755 /opt/firefox/firefox

# Add geckodriver
RUN set -x \
   && curl -sSLO https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VER}/geckodriver-${GECKODRIVER_VER}-linux64.tar.gz \
   && tar zxf geckodriver-*.tar.gz \
   && mv geckodriver /usr/bin/



CMD ["python", "app/__main__.py"]
