#!/bin/bash
set -e

mkdir -p ~/Projects/Alejandro_dev
cd ~/Projects/Alejandro_dev

git clone https://github.com/inventor2525/assistant_merger.git
git clone https://github.com/inventor2525/assistant_interaction.git
git clone https://github.com/inventor2525/RequiredAI.git
git clone https://github.com/inventor2525/Alejandro.git

cd assistant_merger
pip install -e ./
cd ~/Projects/Alejandro_dev

cd assistant_interaction
pip install -e ./
cd ~/Projects/Alejandro_dev

cd RequiredAI
pip install -e ./
cd ~/Projects/Alejandro_dev

cd Alejandro
pip install -e ./
cd ~/Projects/Alejandro_dev
