#!/usr/bin/env bash
set -eu

CONTAINER_NAME="cfy_manager_base"
BASE_IMAGE="cfy_manager_base"
DOCKER_RUN_FLAGS="--name ${CONTAINER_NAME} -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run
 --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN"

echo "Building the base image..."
docker build -t ${BASE_IMAGE} - < Dockerfile

echo "Enabling sshd service to start at boot..."
docker run ${DOCKER_RUN_FLAGS} ${CONTAINER_NAME}
docker exec -d ${CONTAINER_NAME} sh -c "systemctl enable sshd.service"

echo "Saving the base image..."
docker stop $CONTAINER_NAME
docker commit -m "Create CFY Manager base image with sshd" $CONTAINER_NAME $BASE_IMAGE
docker rm $CONTAINER_NAME