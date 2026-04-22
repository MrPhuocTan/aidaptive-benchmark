#!/bin/bash
set -e

echo "Cleaning up broken apt repositories..."
sudo rm -f /etc/apt/sources.list.d/k6.list

echo "Updating system and installing dependencies..."
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv docker.io docker-compose

echo "Installing OHA..."
sudo wget -q https://github.com/hatoo/oha/releases/latest/download/oha-linux-amd64 -O /usr/local/bin/oha
sudo chmod +x /usr/local/bin/oha



echo "Cloning repository..."
rm -rf aidaptive-benchmark
git clone https://github.com/MrPhuocTan/aidaptive-benchmark.git
cd aidaptive-benchmark

echo "Starting Docker services..."
sudo docker-compose up -d

echo "Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "Starting application with nohup..."
nohup python3 -m src > server.log 2>&1 &
echo "Setup complete! App is running in the background."
