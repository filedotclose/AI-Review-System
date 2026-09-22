#!/usr/bin/env bash
set -e

echo "=================================================="
echo "  Setting up AI-Review-System on AWS EC2 (Ubuntu)"
echo "=================================================="

# 1. Setup 2GB Swap Space (Essential for Free Tier 1GB RAM instances)
if [ ! -f /swapfile ]; then
    echo "• Allocating 2GB Swap Memory..."
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "• Swap memory enabled:"
    free -h
fi

# 2. Update System & Install Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "• Installing Docker & Compose Plugin..."
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release ufw
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker $USER
    echo "• Docker installed successfully!"
fi

# 3. Configure Security Firewall (UFW)
echo "• Hardening UFW firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 3000/tcp  # Frontend UI
sudo ufw allow 8000/tcp  # Backend API & Swagger Docs
sudo ufw --force enable

# 4. Build and Launch Containers with Docker Compose
echo "• Building and launching Docker Compose stack..."
sudo docker compose down || true
sudo docker compose up -d --build

SERVER_IP=$(curl -s http://checkip.amazonaws.com || echo "localhost")

echo "=================================================="
echo "  DEPLOYMENT COMPLETE!"
echo "  Frontend UI:   http://${SERVER_IP}:3000"
echo "  Backend Docs:  http://${SERVER_IP}:8000/docs"
echo "=================================================="
