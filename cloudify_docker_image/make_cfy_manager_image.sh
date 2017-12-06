#!/usr/bin/env bash
set -eu
if [ $# -eq 0 ]
  then
    echo "No arguments supplied. Please supply the CFY RPM URL as the first argument."
    exit
fi
# RPM URL must be supplied as the first argument
CFY_RPM_URL=$1
CFY_RPM="cloudify-manager-install.rpm"
CONTAINER_NAME="cfy_manager"
BASE_IMAGE="cfy_manager_base"
IMAGE_PUB_NAME="docker_cfy_manager"
declare -a IMAGE_TAGS=( "latest" "centos7_v1.0_manager_v4.3" )
DOCKER_RUN_FLAGS="--name ${CONTAINER_NAME} -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run
 --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN"
MANAGER_CONFIG_LOCATION="/opt/cloudify"
DOCKER_REPO="manager_images"

set +u
if [ -z "$DOCKER_ID_USER" ] || [ -z "$DOCKER_ID_PASSWORD" ];
  then
    echo "Docker username and password must be set."
    exit
fi
set -u

docker run ${DOCKER_RUN_FLAGS} ${BASE_IMAGE}
CONTAINER_IP=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${CONTAINER_NAME})

echo "Installing cfy..."
docker exec -t $CONTAINER_NAME sh -c "curl $CFY_RPM_URL -o ~/$CFY_RPM &&
 rpm -i ~/$CFY_RPM &&
 rm -f ~/$CFY_RPM"

echo "Creating install config file..."
echo "manager:
  private_ip: ${CONTAINER_IP}
  public_ip: ${CONTAINER_IP}
  set_manager_ip_on_boot: true
  security:
    admin_password: admin" > config.yaml

docker cp config.yaml ${CONTAINER_NAME}:${MANAGER_CONFIG_LOCATION}

echo "Installing manager..."
docker exec -t ${CONTAINER_NAME} sh -c "cfy_manager install"

echo "The Manager's IP is ${CONTAINER_IP}"

echo "Saving the image..."
docker stop $CONTAINER_NAME
docker commit -m "Install CFY manager" $CONTAINER_NAME $IMAGE_PUB_NAME

echo "Removing the used container..."
docker rm $CONTAINER_NAME

echo "Uploading the image..."
docker login -u="${DOCKER_ID_USER}" -p="${DOCKER_ID_PASSWORD}"
for i in "${IMAGE_TAGS[@]}"
do
	docker tag $IMAGE_PUB_NAME ${DOCKER_ID_USER}/${DOCKER_REPO}:$i
done
docker push ${DOCKER_ID_USER}/${DOCKER_REPO}
docker logout
