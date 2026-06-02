#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

log() { printf "[deploy] %s\n" "$*"; }

EC2_INSTANCE="${EC2_INSTANCE:-}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_PATH="${EC2_PATH:-/home/ubuntu/PokeBase}"

if [ -z "$EC2_INSTANCE" ]; then
    log "EC2_INSTANCE must be set"
    exit 1
fi

log "Resolving instance metadata for $EC2_INSTANCE..."
INSTANCE_JSON=$(aws ec2 describe-instances --instance-ids "$EC2_INSTANCE" --query 'Reservations[0].Instances[0]' --output json)
EC2_HOST=$(echo "$INSTANCE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['PublicIpAddress'])")
EC2_AZ=$(echo "$INSTANCE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['Placement']['AvailabilityZone'])")
if [ -z "$EC2_HOST" ] || [ "$EC2_HOST" = "None" ]; then
    log "Failed to resolve public IP for instance $EC2_INSTANCE"
    exit 1
fi
log "Public IP: $EC2_HOST | AZ: $EC2_AZ"

DEPLOY_DIR=$(mktemp -d)
DEPLOY_KEY="$DEPLOY_DIR/ec2_key"
ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -N "" -q

cleanup() {
    rm -rf "$DEPLOY_DIR"
}
trap cleanup EXIT

log "Pushing ephemeral SSH key to instance $EC2_INSTANCE..."
aws ec2-instance-connect send-ssh-public-key \
    --instance-id "$EC2_INSTANCE" \
    --availability-zone "$EC2_AZ" \
    --instance-os-user "$EC2_USER" \
    --ssh-public-key "file://${DEPLOY_KEY}.pub"

log "Syncing files to $EC2_USER@$EC2_HOST:$EC2_PATH..."
rsync -avz --delete \
    -e "ssh -i $DEPLOY_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
    --exclude venv \
    --exclude __pycache__ \
    --exclude '.git' \
    --exclude '.codegraph' \
    --exclude '.opencode' \
    --exclude '.github' \
    --exclude 'data/' \
    --exclude 'static/sprites/' \
    --exclude 'pokebase-latest.zip' \
    ./ "$EC2_USER@$EC2_HOST:$EC2_PATH/"

log "Installing dependencies on EC2..."
ssh -i "$DEPLOY_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$EC2_USER@$EC2_HOST" bash -s "$EC2_PATH" <<'REMOTE'
set -euo pipefail
cd "$1"

if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --quiet -r requirements.txt

mkdir -p data static/sprites
REMOTE

log "Restarting app..."
ssh -i "$DEPLOY_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$EC2_USER@$EC2_HOST" sudo systemctl daemon-reload
ssh -i "$DEPLOY_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$EC2_USER@$EC2_HOST" sudo systemctl restart pokebase
ssh -i "$DEPLOY_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$EC2_USER@$EC2_HOST" sudo systemctl status pokebase --no-pager | head -5
log "App restarted"

log "Deploy complete!"
