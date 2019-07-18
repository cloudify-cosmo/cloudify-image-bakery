#!/bin/bash

set -e

if [ $# -lt 2 ]; then
    echo "Missing arguments."
    echo "Usage: $0 src_config_path dst_config_path"
    exit
fi

src_config_path=$1
dst_config_path=$2

cp $src_config_path $dst_config_path
cfy_manager configure --private-ip $POD_IP --public-ip $POD_IP