#!/usr/bin/env bash
set -eu

CONTAINER_NAME="cfy-manager-base"
BASE_IMAGE="latest-centos7-base-image"
DOCKER_RUN_FLAGS="--name ${CONTAINER_NAME} -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run
 --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN"
declare -a IMAGE_TAGS=( "latest-centos7-base-image" "centos7-v1.2" )
DOCKER_REPO="community"

set +u
if [ -z "$DOCKER_BUILD_ID" ] || [ -z "$DOCKER_BUILD_PASSWORD" ] || [ -z "$DOCKER_ORGANIZATION" ];
  then
    echo "Docker username and password must be set."
    exit
fi
set -u

echo "Building the base image..."
docker build -t ${BASE_IMAGE} - < Dockerfile

echo "Enabling sshd service to start at boot..."
docker run ${DOCKER_RUN_FLAGS} ${BASE_IMAGE}
docker exec -d ${CONTAINER_NAME} sh -c "systemctl enable sshd.service"

echo "Saving the base image..."
docker commit -m "Create CFY Manager base image with sshd" $CONTAINER_NAME $BASE_IMAGE
docker stop $CONTAINER_NAME

echo "Removing the used container..."
docker rm $CONTAINER_NAME

echo "Uploading the image..."
docker login -u="${DOCKER_BUILD_ID}" -p="${DOCKER_BUILD_PASSWORD}"
for i in "${IMAGE_TAGS[@]}"
do
	docker tag $BASE_IMAGE ${DOCKER_ORGANIZATION}/${DOCKER_REPO}:$i
done
docker push ${DOCKER_ORGANIZATION}/${DOCKER_REPO}
docker logout
