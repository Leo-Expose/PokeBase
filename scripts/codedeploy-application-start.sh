#!/usr/bin/env bash
set -euo pipefail

cd /home/admin/PokeBase

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/pokebase"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REPOSITORY_URI"

# Pull from ECR
docker pull "$REPOSITORY_URI:latest"

S3_DATA_URL="https://pokebase-data.s3.ap-south-1.amazonaws.com/pokebase-data.tar.gz"

# Run the container with S3 data URL
docker run -d \
  --name pokebase \
  -p 5000:5000 \
  -e POKEBASE_DATA_URL="${S3_DATA_URL}" \
  -v pokebase-data:/app/data \
  -v pokebase-sprites:/app/static/sprites \
  --restart unless-stopped \
  "$REPOSITORY_URI:latest"
