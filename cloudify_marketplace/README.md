# Cloudify AMI builder

## How to use this?

# TODO: Improve prerequisites instructions and listing- make script to verify? Note what OSes we have run packer on to generate this
1. Install prerequisites (packer, aws CLI(?), openstack CLI(?))
2. Copy the sample vars file and alter it for the environment(s) you wish to generate images for- e.g. modify all aws settings if you only wish to generate images on AWS. Inputs for each environment are prefixed by the environment name (aws or openstack). You may also set the cloudify version to use a version other than 3.3.1.
3. Assuming you have copied the example inputs to inputs.json:
 3.1 To build on all environments: Run `packer build --var-file inputs.json cloudify.json`
 3.2 To build on a specific environment specify that environment name as the only one: Run `packer build --var-file inputs.json --only=aws cloudify.json` or `packer build --var-file inputs.json --only=openstack cloudify.json`

## Prerequisites

1. Packer 0.8.6+ (Older versions were not tested)

## Copying AMI to different regions (manually)

1. Copy: `aws ec2 copy-image --source-image-id <source_ami> --source-region <region> --region <dest_region> --name "Cloudify <version> Release"`
2. Make public: `aws ec2 modify-image-attribute --image-id <image_id> --region <image_region> --launch-permission "{\"Add\":[{\"Group\":\"all\"}]}"`
