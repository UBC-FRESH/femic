#!/usr/bin/env bash
# Copy to config/credentials/arbutus_env.sh and fill in real values.
# This template is safe to commit; concrete credential files are gitignored.

export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="ca-west-1"
export S3_ENDPOINT_URL="https://object-arbutus.alliancecan.ca"

# Optional explicit bucket name for your DataLad special remote bootstrap.
export S3_BUCKET_NAME="UNIQUE_BUCKET_NAME"
