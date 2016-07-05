# Cloudify AMI builder

## Prerequisites
> A UNIX-like OS is required for running Packer. Builds aren't supported on Windows

* [packer](https://www.packer.io/intro/getting-started/setup.html) (tested on 0.8.6)
* zip
* Account credentials for each cloud platform you want to build on.
* An image ID to base the new image on.
* OpenStack specific:
  * endpoint address for your OpenStack provider
  * your tenant name
  * your floating IP pool name (packer will provision an IP within that pool and remove it when it's finished)
  * IDs for:
    * a network
    * a security group
* vSphere specific:
  * SSH User & Password


## How to use this?

1. Clone the image bakery repo
2. cd into the image bakery path
    ```bash
    git clone https://github.com/cloudify-cosmo/cloudify-image-bakery.git
    cd cloudify-image-bakery/cloudify_marketplace
    ```

3. Copy inputs-example.json and edit with your favourite editor
    ```bash
    cp inputs-example.json inputs.json
    nano inputs.json
    ```

    Point `packer` at a CentOS 7(TODO?) image in your cloud:
    ```json
    "aws_source_ami": "ami-91feb7fb",
    "openstack_image_flavor": "d87de0ca-9c0e-4759-a704-8621883c3415",
    ```

> Fill in the fields for each cloud platform you intend to use in the same file. If you don't plan to use OpenStack for example you can leave the 'openstack_' prefixed fields as they are.

 4. Run `packer`
    ```bash
    $ packer build --only=aws,openstack --var-file=inputs.json cloudify.json
    ```

    Change the list passed to `--only` depending on which platforms you are building for, e.g. to build only for AWS: `--only=aws`


## Copying AMI to different regions (manually)

1. Copy: `aws ec2 copy-image --source-image-id <source_ami> --source-region <region> --region <dest_region> --name "Cloudify <version> Release"`
2. Make public: `aws ec2 modify-image-attribute --image-id <image_id> --region <image_region> --launch-permission "{\"Add\":[{\"Group\":\"all\"}]}"`
