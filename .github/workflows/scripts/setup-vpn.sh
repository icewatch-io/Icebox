set -e

sudo apt update
sudo apt install -y wireguard

# Generate server keys
cd /etc/wireguard
umask 077
if ! wg genkey | sudo tee privatekey | wg pubkey | sudo tee publickey; then
    echo "Failed to generate WireGuard keys" >&2
    exit 1
fi

# Create server config
sudo tee /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat privatekey)
Address = 10.0.0.1/24
ListenPort = 51820
SaveConfig = false

[Peer]
PublicKey = CLIENT_PUBLIC_KEY_PLACEHOLDER
AllowedIPs = 10.0.0.2/32
EOF

# Start WireGuard and enable on boot
if ! sudo systemctl enable --now wg-quick@wg0; then
    echo "Failed to start WireGuard service" >&2
    exit 1
fi

echo "$(cat publickey)"
