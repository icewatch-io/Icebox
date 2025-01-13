set -e

echo "Starting end-to-end"

cleanup() {
    rm -f \
        client_privatekey \
        client_publickey \
        oci-install.sh \
        wg-client.conf
}
trap cleanup EXIT

sudo apt update
sudo apt install -y \
    wireguard \
    jq

# Generate SSH key
KEY_NAME="test-$(date +%s%N | md5sum | head -c 8)"
SSH_KEY="$HOME/.ssh/$KEY_NAME"
ssh-keygen -t rsa -b 4096 -f "$SSH_KEY" -N ""

# Generate client WireGuard keys
if ! wg genkey | tee client_privatekey | wg pubkey | tee client_publickey; then
    echo "Failed to generate WireGuard keys"
    exit 1
fi
WG_CLIENT_PUBKEY=$(cat client_publickey)

# Download OCI binary
curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh > oci-install.sh
chmod +x oci-install.sh
./oci-install.sh --accept-all-defaults
OCI=~/bin/oci
mkdir ~/.oci
echo "$OCI_API_KEY_PRIV" > ~/.oci/oci_api_key.pem
echo "$OCI_API_KEY_PUB" > ~/.oci/oci_api_key_public.pem
chmod 600 ~/.oci/oci_api_key.pem ~/.oci/oci_api_key_public.pem

# Start instance in OCI
SERVER_IP=$(bash .github/workers/scripts/start-instance.sh $SSH_KEY)
if [ -z "$SERVER_IP" ]; then
    echo "Failed to get server IP"
    exit 1
fi

# TODO: Open port for instance
echo "Waiting for instance to be ready..."
sleep 30

# Install WireGuard in OCI instance
sed -i "s/CLIENT_PUBLIC_KEY_PLACEHOLDER/$WG_CLIENT_PUBKEY/" .github/workers/scripts/setup-vpn.sh
scp -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" .github/workers/scripts/setup-vpn.sh ubuntu@$SERVER_IP:/tmp
SERVER_PUBLIC_KEY=$(ssh -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" ubuntu@$SERVER_IP "bash /tmp/setup-vpn.sh")
if [ -z "$SERVER_PUBLIC_KEY" ]; then
    echo "Failed to get server public key"
    exit 1
fi

# Create client config
tee wg-client.conf << EOF
[Interface]
PrivateKey = $(cat client_privatekey)
Address = 10.0.0.2/24

[Peer]
PublicKey = $SERVER_PUBLIC_KEY
Endpoint = $SERVER_IP:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
EOF

# Connect to VPN
if ! sudo wg-quick up wg-client.conf; then
    echo "Failed to establish WireGuard connection"
    exit 1
fi
