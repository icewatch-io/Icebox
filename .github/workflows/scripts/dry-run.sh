set -e

echo "Installing updates..."
sudo apt-get remove -y needrestart
sudo apt-get update
sudo apt-get upgrade -y

REPO_URL="https://github.com/${GITHUB_REPOSITORY}"
REPO_RAW_URL="https://raw.githubusercontent.com/${GITHUB_REPOSITORY}"
BRANCH_NAME=${GITHUB_HEAD_REF}

echo "Starting dry run..."
echo "PR repository: ${REPO_URL}"
echo "PR branch: ${BRANCH_NAME}"

# Download the setup script from the PR's branch
echo "Downloading setup script..."
if ! curl -sf "${REPO_RAW_URL}/${BRANCH_NAME}/setup.sh" -o setup.sh; then
    echo "Error: failed to download setup.sh"
    exit 1
fi
ls -l setup.sh

# Modify the setup script to use the PR's branch
echo "Modifying setup script..."
sed -i "s|git clone https://github.com/icewatch-io/icebox.git|git clone -b ${BRANCH_NAME} ${REPO_URL}|g" setup.sh
if ! grep -q "${BRANCH_NAME}" setup.sh; then
    echo "Error: failed to update branch in downloaded setup.sh"
    exit 1
fi

echo "Running setup script..."
chmod +x setup.sh
sudo bash -x setup.sh 2>&1

echo "Verifying service start..."
if systemctl is-active icebox &>/dev/null; then
    echo "Success: icebox service is active"
else
    echo "Error: icebox service is not active"
    exit 1
fi

echo "Verifying iptables rules are set..."
if sudo iptables -L | grep "SNOWDOG"; then
    echo "Success: SNOWDOG iptables rules found"
else
    echo "Error: SNOWDOG iptables rules not found after initial service start"
    exit 1
fi
if sudo iptables -L | grep "ICICLE"; then
    echo "Success: ICICLE iptables rules found"
else
    echo "Error: ICICLE iptables rules not found after initial service start"
    exit 1
fi

echo "Verifying service stop..."
sudo systemctl stop icebox
if systemctl is-active icebox &>/dev/null; then
    echo "Error: icebox service failed to stop"
    exit 1
else
    echo "Success: icebox service stopped"
fi

echo "Verifying iptables rules are cleared after service stop..."
if sudo iptables -L | grep -q "SNOWDOG\|ICICLE"; then
    echo "Error: iptables rules not cleared after service stop"
    exit 1
else
    echo "Success: iptables rules cleared"
fi

echo "Success: dry run completed"
