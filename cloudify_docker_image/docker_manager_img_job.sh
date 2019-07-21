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

IMAGE_REPOSITORY="$(docker images | grep cloudify- | awk 'NR==1{print $1}')"
if [[ "$IMAGE_TYPE" == "manager-aio" ]]; then
    docker image save -o cloudify-docker-manager-$CLOUDIFY_TAG.tar $IMAGE_REPOSITORY:latest
else
    docker image save -o cloudify-${IMAGE_TYPE,,}-docker-$CLOUDIFY_TAG.tar $IMAGE_REPOSITORY:latest
fi
upload_to_s3 tar