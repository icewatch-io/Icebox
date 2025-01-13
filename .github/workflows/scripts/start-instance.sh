set -e

OCI=~/bin/oci
SSH_KEY=$1

#OCI_CID
#OCI_COMP_ID
#OCI_SUBNET_ID
#OCI_AVAILABILITY_DOMAIN
#OCI_SHAPE
#OCI_IMAGE_ID

VM_CREATE_RESULT=$($OCI compute instance launch \
  --compartment-id "$OCI_COMP_ID" \
  --shape "$OCI_SHAPE" \
  --subnet-id "$OCI_SUBNET_ID" \
  --availability-domain "$OCI_AVAILABILITY_DOMAIN" \
  --source-details "{\"sourceType\": \"image\", \"imageId\": \"$OCI_IMAGE_ID\"}" \
  --metadata "{\"ssh_authorized_keys\": \"$(cat $SSH_KEY)\"}")
echo "VM creation result: $VM_CREATE_RESULT"

if echo "$VM_CREATE_RESULT" | jq -e '.data.id' >/dev/null 2>&1; then
    INSTANCE_ID=$(echo "$VM_CREATE_RESULT" | jq -r '.data.id')
    echo "Successfully created instance with ID: $INSTANCE_ID"
else
    echo "Error: Failed to create instance or get instance ID"
    echo "Response did not contain expected data structure"
    exit 1
fi

GET_VNIC_RESULT=$($OCI compute instance list-vnics --instance-id "$INSTANCE_ID")
echo "Get VNIC result: $GET_VNIC_RESULT"
if echo "$GET_VNIC_RESULT" | jq -e '.data[0]."public-ip"' >/dev/null 2>&1; then
    PUBLIC_IP=$(echo "$GET_VNIC_RESULT" | jq -r '.data[0]."public-ip"')
    echo "Successfully retrieved public IP: $PUBLIC_IP"
else
    echo "Error: Failed to get public IP"
    echo "Response did not contain expected VNIC data"
    exit 1
fi

echo $PUBLIC_IP
