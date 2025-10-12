#!/bin/bash
# AWS SSO Login and Credential Export Script
# Usage: source ./aws-sso-login.sh [profile-name]

set -e

PROFILE="${1:-default}"

echo "=== AWS SSO Login Script ==="
echo "Profile: $PROFILE"
echo ""

# Check if AWS config exists
if [ ! -f ~/.aws/config ]; then
    echo "⚠ AWS config not found at ~/.aws/config"
    echo "Please run: aws configure sso"
    exit 1
fi

echo "Logging in to AWS SSO..."
aws sso login --profile "$PROFILE"

if [ $? -eq 0 ]; then
    echo "✓ SSO login successful"
    echo ""
    echo "Exporting credentials to environment..."
    eval $(aws configure export-credentials --profile "$PROFILE" --format env)
    
    if [ $? -eq 0 ]; then
        echo "✓ Credentials exported successfully"
        echo ""
        echo "Environment variables set:"
        echo "  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:20}..."
        echo "  AWS_SESSION_TOKEN: [set]"
    else
        echo "✗ Failed to export credentials"
        exit 1
    fi
else
    echo "✗ SSO login failed"
    exit 1
fi