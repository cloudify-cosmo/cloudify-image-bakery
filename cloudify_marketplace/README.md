# Cloudify AMI builder

## How to use this?

1. Install prerequisites
2. Run `packer build -var 'cloudify_version=<VERSION>' cloudify_aws.json` while replacing `<VERSION>` with the desired Cloudify manager version

## Prerequisites

1. Packer 0.8.6+ (Older versions were not tested)

## Copying AMI to different regions (manually)

1. Copy: `aws ec2 copy-image --source-image-id <source_ami> --source-region <region> --region <dest_region> --name "Cloudify <version> Release"`
2. Make public: `aws ec2 modify-image-attribute --image-id <image_id> --region <image_region> --launch-permission "{\"Add\":[{\"Group\":\"all\"}]}"`
