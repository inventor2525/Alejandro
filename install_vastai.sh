#!/bin/bash
set -e

INSTALL_DIR="${HOME}/projects"

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git ffmpeg > /dev/null 2>&1

mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

[ ! -d "Alejandro" ] && git clone -q https://github.com/inventor2525/Alejandro.git
[ ! -d "RequiredAI" ] && git clone -q https://github.com/inventor2525/RequiredAI.git
[ ! -d "assistant_merger" ] && git clone -q https://github.com/inventor2525/assistant_merger.git
[ ! -d "assistant_interaction" ] && git clone -q https://github.com/inventor2525/assistant_interaction.git
[ ! -d "WhisperLiveKit" ] && git clone -q https://github.com/QuentinFuxa/WhisperLiveKit.git

python3 -m venv venv
source venv/bin/activate

cd RequiredAI && pip install -q -e . && cd ..
cd assistant_merger && pip install -q -e . && cd ..
cd assistant_interaction && pip install -q -e . && cd ..
cd Alejandro && pip install -q -e . && cd ..
cd WhisperLiveKit && pip install -q -e . && cd ..

pip install -q websocket-client flask flask-socketio groq nltk

python3 -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)"

echo "source ${INSTALL_DIR}/venv/bin/activate" > "${INSTALL_DIR}/activate.sh"
chmod +x "${INSTALL_DIR}/activate.sh"
