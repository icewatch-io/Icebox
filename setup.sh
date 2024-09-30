#!/bin/bash
set -e

if [ -z "$ICEBOX_USER" ]; then
    ICEBOX_USER="icebox"
fi

if [ -z "$DEVICE_IP" ]; then
    DEVICE_IP=$(ip route get 1 | awk '{print $7; exit}')
fi

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit
fi

echo "Installing Icebox to run as $ICEBOX_USER with IP address $DEVICE_IP"

echo "Setting up iptables rules for logging"
iptables -A INPUT -d $DEVICE_IP -p tcp -m conntrack --ctstate NEW -j LOG --log-prefix "ICICLE: "
iptables -A INPUT -d $DEVICE_IP -p udp -m conntrack --ctstate NEW -j LOG --log-prefix "ICICLE: "

iptables -A INPUT -m addrtype --dst-type BROADCAST -j LOG --log-prefix "SNOWDOG: "
iptables -A INPUT -m addrtype --dst-type MULTICAST -j LOG --log-prefix "SNOWDOG: "
iptables -A INPUT -m addrtype --dst-type ANYCAST -j LOG --log-prefix "SNOWDOG: "

echo "Installing iptables-persistent to save rules across reboots"
apt-get update
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean true | sudo debconf-set-selections
DEBIAN_FRONTEND=noninteractive sudo apt-get install -y iptables-persistent

echo "Configuring user"
if [ ! "$(id -u "$ICEBOX_USER" 2>/dev/null)" ]; then
    echo "Adding user $ICEBOX_USER"
    useradd -r -s /usr/sbin/nologin "$ICEBOX_USER"
fi
usermod -aG adm icebox

echo "Setting up directories"
mkdir -p /opt/icebox/icebox
mkdir -p /etc/icebox
mkdir -p /var/log/icebox

echo "Installing Icebox"
DEPLOY_DIR=$(mktemp -d)
cd "$DEPLOY_DIR"
git clone https://github.com/icewatch-io/icebox.git
cd icebox
mv src/* /opt/icebox/icebox

if [ ! -f /etc/icebox/config.json ]; then
    echo "Using example config"
    cp "$DEPLOY_DIR/icebox/config-example.json" /etc/icebox/config.json
fi

chown -R $ICEBOX_USER:$ICEBOX_USER /opt/icebox
chown -R $ICEBOX_USER:$ICEBOX_USER /var/log/icebox
cd /opt/icebox
rm -rf "$DEPLOY_DIR"

echo "Setting up Icebox service"
if [ ! -f /etc/systemd/system/icebox.service ]; then
    cat >/etc/systemd/system/icebox.service <<EOF
[Unit]
Description=Icebox

[Service]
Type=simple
ExecStart=python3 /opt/icebox/icebox
WorkingDirectory=/opt/icebox/
User=$ICEBOX_USER
Group=$ICEBOX_USER
Restart=always
RestartSec=1s

[Install]
WantedBy=multi-user.target
EOF
fi

echo "Starting Icebox service"
systemctl daemon-reload
systemctl enable icebox --now
