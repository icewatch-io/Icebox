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

# Cleanup old rules
if [ -f /etc/iptables/rules.v4 ]; then
    gecho "Removing existing iptables rules"
    temp=$(mktemp)
    cat /etc/iptables/rules.v4 | grep -v "SNOWDOG\|ICICLE" > $temp
    cat $temp > /etc/iptables/rules.v4
    rm $temp
fi

gecho "Setting up iptables rules for logging"
iptables -A INPUT -d $DEVICE_IP -p tcp -m conntrack --ctstate NEW -j LOG --log-prefix "ICICLE: "
iptables -A INPUT -d $DEVICE_IP -p udp -m conntrack --ctstate NEW -j LOG --log-prefix "ICICLE: "

iptables -A INPUT -m addrtype --dst-type BROADCAST -j LOG --log-prefix "SNOWDOG: "
iptables -A INPUT -m addrtype --dst-type MULTICAST -j LOG --log-prefix "SNOWDOG: "
iptables -A INPUT -m addrtype --dst-type ANYCAST -j LOG --log-prefix "SNOWDOG: "

gecho "Installing iptables-persistent to save rules across reboots"
apt-get update
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean true | sudo debconf-set-selections
DEBIAN_FRONTEND=noninteractive sudo apt-get install -y iptables-persistent

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

gecho "Installing Icebox"
DEPLOY_DIR=$(mktemp -d)
cd "$DEPLOY_DIR"
git clone https://github.com/icewatch-io/icebox.git
cd icebox
mv src/* /opt/icebox/icebox

if [ ! -f /etc/icebox/config.json ]; then
    gecho "Using example config"
    cp "$DEPLOY_DIR/icebox/config-example.json" /etc/icebox/config.json
else
    gecho "Using existing config"
fi

chown -R $ICEBOX_USER:$ICEBOX_USER /opt/icebox
chown -R $ICEBOX_USER:$ICEBOX_USER /var/log/icebox
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
ExecStart=python3 /opt/icebox/icebox
WorkingDirectory=/opt/icebox/
User=$ICEBOX_USER
Group=$ICEBOX_USER
Restart=always
RestartSec=1s

[Install]
WantedBy=multi-user.target
EOF

gecho "Starting Icebox service"
systemctl daemon-reload
systemctl enable icebox --now

gecho "Icebox installed and started. Reboot recommended."
