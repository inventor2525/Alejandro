#!/bin/bash
set -e

apt-get update -qq && apt-get install -y -qq python3-pip git ffmpeg >/dev/null 2>&1

cd ~
python3 -m venv venv
. venv/bin/activate

git clone -q https://github.com/inventor2525/RequiredAI.git && cd RequiredAI && pip install -q -e . && cd ..
git clone -q https://github.com/inventor2525/assistant_merger.git && cd assistant_merger && pip install -q -e . && cd ..
git clone -q https://github.com/inventor2525/assistant_interaction.git && cd assistant_interaction && pip install -q -e . && cd ..
git clone -q https://github.com/inventor2525/Alejandro.git && cd Alejandro && pip install -q -e . && cd ..
git clone -q https://github.com/QuentinFuxa/WhisperLiveKit.git && cd WhisperLiveKit && pip install -q -e . && cd ..

pip install -q websocket-client
