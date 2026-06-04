#!/usr/bin/env bash
set -euo pipefail

cd /home/ubuntu/PokeBase

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/pokebase"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REPOSITORY_URI"

# Pull from ECR and tag so docker-compose.yml (image: pokebase) finds it
docker pull "$REPOSITORY_URI:latest"
docker tag "$REPOSITORY_URI:latest" pokebase:latest

# Inject POKEBASE_DATA_URL from CodeBuild env or fall back to GitHub
export POKEBASE_DATA_URL="${POKEBASE_DATA_URL:-}"
docker compose up -d
