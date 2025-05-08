#!/bin/bash
set -e

# Green and red gecho
gecho() { echo -e "\033[1;32m$1\033[0m"; }
recho() { echo -e "\033[1;31m$1\033[0m"; }

# Check prerequisites
if [ ! -f "/etc/lsb-release" ] || [ -z "$(grep '22.04' /etc/lsb-release)" ]; then
    recho "ERROR: The official Icebox setup script only supports Ubuntu Server 22.04"
    recho "You may delete this check and run the script at your own risk."
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    recho "ERROR: Must be run as root."
    exit 1
fi

# Check config
if [ -z "$ICEBOX_USER" ]; then
    ICEBOX_USER="icebox"
fi

if [ -z "$DEVICE_IP" ]; then
    DEVICE_IP=$(ip route get 1 | awk '{print $7; exit}')
fi

gecho "Installing Icebox to run as $ICEBOX_USER with IP address $DEVICE_IP"

gecho "Configuring user"
if [ ! "$(id -u "$ICEBOX_USER" 2>/dev/null)" ]; then
    gecho "Adding user $ICEBOX_USER"
    useradd -r -s /usr/sbin/nologin "$ICEBOX_USER"
fi
usermod -aG adm icebox

if [ -d /opt/icebox/icebox ]; then
    gecho "Removing old Icebox installation"
    rm -fr /opt/icebox/icebox
fi

gecho "Setting up directories"
mkdir -p /opt/icebox/icebox
mkdir -p /etc/icebox
mkdir -p /var/log/icebox

touch /etc/icebox/config-icewatch.json
chown $ICEBOX_USER:$ICEBOX_USER /etc/icebox/config-icewatch.json

gecho "Installing Icebox"
DEPLOY_DIR=$(mktemp -d)
cd "$DEPLOY_DIR"
git clone https://github.com/icewatch-io/icebox.git
if [ -d Icebox ]; then
  mv Icebox icebox
fi
cd icebox
mv src/icebox /opt/icebox
chmod +x /opt/icebox/icebox/iptables.sh

if [ ! -f /etc/icebox/config.json ]; then
    gecho "Using example config"
    cp "$DEPLOY_DIR/Icebox/config-example.json" /etc/icebox/config.json
else
    gecho "Using existing config"
fi

chown -R $ICEBOX_USER:$ICEBOX_USER /opt/icebox
chown -R $ICEBOX_USER:$ICEBOX_USER /var/log/icebox
chmod -R g+x /opt/icebox/icebox
cd /opt/icebox
rm -rf "$DEPLOY_DIR"

gecho "Setting up Icebox service"
if [ -f /etc/systemd/system/icebox.service ]; then
    rm /etc/systemd/system/icebox.service
fi
cat >/etc/systemd/system/icebox.service <<EOF
[Unit]
Description=Icebox

[Service]
Type=simple
ExecStartPre=+/opt/icebox/icebox/iptables.sh add
ExecStopPost=+/opt/icebox/icebox/iptables.sh remove

ExecStart=python3 -B /opt/icebox/icebox
WorkingDirectory=/opt/icebox/
User=$ICEBOX_USER
Group=$ICEBOX_USER
Restart=always
RestartSec=1s
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
EOF

gecho "Starting Icebox service"
systemctl daemon-reload
systemctl enable icebox --now

gecho "Icebox installed and started. Reboot recommended."
