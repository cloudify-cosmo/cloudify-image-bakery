# Cloudify AMI builder

## How to use this?

1. Install prerequisites
2. Run `packer build -var 'cloudify_version=<VERSION>' cloudify_aws.json` while replacing `<VERSION>` with the desired Cloudify manager version

## Prerequisites

1. Packer 0.8.6+ (Older versions were not tested)
