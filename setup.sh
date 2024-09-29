#!/bin/bash

USER="icebox"
DEVICE_IP=$(ip route get 1 | awk '{print $7; exit}')

echo "Installing Icebox to run as $USER with IP address $DEVICE_IP"

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
if [ ! "$(id -u "$USER" 2>/dev/null)" ]; then
    echo "Adding user $USER"
    useradd -r -s /usr/sbin/nologin "$USER"
fi
usermod -aG adm icebox

echo "Setting up config"
if [ ! -d /etc/icebox ]; then
    mkdir /etc/icebox
fi
if [ ! -f /etc/icebox/config.json ]; then
    cp config-example.json /etc/icebox/config.json
fi

echo "Setting up required directories"
if [ ! -d /opt/icebox ]; then
    mkdir /opt/icebox
fi
if [ ! -d /opt/icebox/icebox ]; then
    mkdir /opt/icebox/icebox
fi
chown -R $USER:$USER /opt/icebox

if [ ! -d /var/log/icebox ]; then
    mkdir /var/log/icebox
fi
chown $USER:$USER /var/log/icebox

echo "Downloadng Icebox"
DEPLOY_DIR=$(mktemp -d)
cd "$DEPLOY_DIR"
git clone git@github.com:icewatch-io/icebox.git
cd icebox
mv src/* /opt/icebox/icebox

echo "Setting up Icebox service"
if [ ! -f /etc/systemd/system/icebox.service ]; then
    cat >/etc/systemd/system/icebox.service <<EOF
[Unit]
Description=Icebox

[Service]
Type=simple
ExecStart=python3 /opt/icebox/icebox
WorkingDirectory=/opt/icebox/
User=$USER
Group=$USER
Restart=always
RestartSec=1s

[Install]
WantedBy=multi-user.target
EOF
fi

echo "Starting Icebox service"
systemctl daemon-reload
systemctl enable icebox --now
