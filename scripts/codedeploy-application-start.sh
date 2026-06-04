#!/usr/bin/env bash
set -euo pipefail

cd /home/admin/PokeBase

ACCOUNT_ID="970006065759"
REPOSITORY_URI="${ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com/pokebase"
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin "$REPOSITORY_URI" || true

# Pull from ECR
docker pull "$REPOSITORY_URI:latest"

S3_DATA_URL="https://pokebase-data.s3.ap-south-1.amazonaws.com/pokebase-data.tar.gz"

# Remove old container if exists
docker rm -f pokebase 2>/dev/null || true

# Run the container with S3 data URL
docker run -d \
  --name pokebase \
  -p 5000:5000 \
  -e POKEBASE_DATA_URL="${S3_DATA_URL}" \
  -v pokebase-data:/app/data \
  -v pokebase-sprites:/app/static/sprites \
  --restart unless-stopped \
  "$REPOSITORY_URI:latest"
