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

# 2. Update System & Install Docker, Compose Plugin & Fail2ban
if ! command -v docker &> /dev/null; then
    echo "• Installing Docker, Compose Plugin & Security Tools..."
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release ufw fail2ban
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker $USER
    echo "• Docker installed successfully!"
fi

# 3. Configure Fail2ban for SSH Brute-Force Defense
echo "• Enabling Fail2ban for SSH defense..."
sudo systemctl enable --now fail2ban || true

# 4. Configure Hardened UFW Firewall (Only Ports 22, 80, 443)
echo "• Hardening UFW firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH (Lock down to admin IP in AWS SG)
sudo ufw allow 80/tcp    # HTTP (Reverse Proxy)
sudo ufw allow 443/tcp   # HTTPS (SSL/TLS)
# Ports 3000 & 8000 are explicitly NOT exposed to host/public
sudo ufw --force enable

# 5. Build and Launch Containers with Docker Compose
echo "• Building and launching Docker Compose stack with Nginx..."
sudo docker compose down || true
sudo docker compose up -d --build

SERVER_IP=$(curl -s http://checkip.amazonaws.com || echo "localhost")

echo "=================================================="
echo "  DEPLOYMENT COMPLETE (PROTECTED BY NGINX PROXY)!"
echo "  Application UI:    http://${SERVER_IP}"
echo "  API Documentation: http://${SERVER_IP}/docs"
echo "  Rate Limiting:     ACTIVE (Auth: 3r/s, API: 10r/s)"
echo "=================================================="
