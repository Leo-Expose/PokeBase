#!/usr/bin/env bash
set -euo pipefail

REGION="${1:-ap-south-1}"
REPO_NAME="pokebase"

echo "Creating ECR repository '$REPO_NAME' in $REGION..."

if aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$REGION" &>/dev/null; then
    echo "Repository already exists."
else
    aws ecr create-repository \
        --repository-name "$REPO_NAME" \
        --region "$REGION" \
        --image-scanning-configuration scanOnPush=true \
        --output json
    echo "Repository created."
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo ""
echo "=== ECR Repository URI ==="
echo "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"
echo ""
echo "=== Make sure CodeBuild project has these environment variables ==="
echo "  - AWS_REGION (should match CodeBuild project region)"
echo "  - Enable 'Privileged' flag in CodeBuild project (required for Docker)"
echo ""
echo "=== EC2 Instance Profile needs these permissions ==="
cat <<PERMS
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability"
            ],
            "Resource": "arn:aws:ecr:${REGION}:${ACCOUNT_ID}:repository/${REPO_NAME}"
        },
        {
            "Effect": "Allow",
            "Action": "ecr:GetAuthorizationToken",
            "Resource": "*"
        }
    ]
}
PERMS
