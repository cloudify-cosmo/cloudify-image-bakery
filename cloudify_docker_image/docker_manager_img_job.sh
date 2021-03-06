#!/bin/bash -e -x

sudo systemctl restart docker.service
set +e
if [[ $(docker ps -a -q) ]];then
    docker stop $(docker ps -a -q)
    docker rm -v -f $(docker ps -a -q)
fi
if [[ $(docker images -q) ]];then
    docker rmi -f $(docker images -q)
fi
if [[ $(docker images -q) ]];then
    echo "The following docker images were not deleted: $(docker images -a)"
    exit
fi	
set -e

docker pull $DOCKER_ORGANIZATION/community:latest-centos7-base-image
bash make_cfy_manager_image.sh $INSTALL_RPM_URL ${IMAGE_TYPE}

docker image save -o cloudify-manager-aio-docker-$CLOUDIFY_TAG.tar cloudify-manager-aio:latest
