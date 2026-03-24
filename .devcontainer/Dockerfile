FROM ubuntu

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get install -y git python3-pip ffmpeg

RUN pip3 install --break-system-packages -U bidict certifi docker git+https://github.com/Renaud11232/nextcord.git@aead-xchacha20-poly1305-rtpsize pynacl requests websockets