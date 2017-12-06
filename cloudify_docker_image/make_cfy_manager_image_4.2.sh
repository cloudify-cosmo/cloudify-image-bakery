#!/usr/bin/env bash
set -eu
if [ $# -eq 0 ]
  then
    echo "No arguments supplied. Please supply the CFY CLI RPM URL as the first argument."
    exit
fi
# RPM URL must be supplied as the first argument
CLI_PACKAGE_URL=$1
CLI_RPM="cloudify-cli.rpm"
MANAGER_BLUEPRINTS_PATH="/opt/cfy/cloudify-manager-blueprints"
MANAGER_BLUEPRINT_PATH="${MANAGER_BLUEPRINTS_PATH}/simple-manager-blueprint.yaml"
INPUTS_FILE_PATH="/root/config.yaml"
CLOUDIFY_MANAGER_USERNAME="admin"
CLOUDIFY_MANAGER_PASSWORD="admin"
CONTAINER_NAME="cfy_manager"
IMAGE_PUB_NAME="docker_cfy_manager_4.2"
BASE_IMAGE="cfy_manager_base"
DOCKER_RUN_FLAGS="--name ${CONTAINER_NAME} -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run
 --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN"
DOCKER_REPO="community"
declare -a IMAGE_TAGS=( "centos7_v1.0_manager_v4.2_community" )

set +u
if [ -z "$DOCKER_ID_USER" ] || [ -z "$DOCKER_ID_PASSWORD" ];
  then
    echo "Docker username and password must be set."
    exit
fi
set -u

docker run ${DOCKER_RUN_FLAGS} ${BASE_IMAGE}
CONTAINER_IP=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${CONTAINER_NAME})

echo "Creating install config file..."
echo "public_ip: ${CONTAINER_IP}
private_ip: ${CONTAINER_IP}
ssh_user: root
ssh_key_filename: /root/.ssh/id_rsa
ssl_enabled: false
admin_username: ${CLOUDIFY_MANAGER_USERNAME}
admin_password: ${CLOUDIFY_MANAGER_PASSWORD}
set_manager_ip_on_boot: true" > config.yaml

docker cp config.yaml ${CONTAINER_NAME}:${INPUTS_FILE_PATH}

echo "Downloading Cloudify's CLI from: ${CLI_PACKAGE_URL}"
docker exec -t ${CONTAINER_NAME} sh -c "curl ${CLI_PACKAGE_URL} -o ~/${CLI_RPM}"

echo "Installing Cloudify's CLI..."
docker exec -t ${CONTAINER_NAME} sh -c "rpm -i ~/${CLI_RPM}"

echo "Generating public/private key pair and adding to authorized_keys..."
docker exec -t ${CONTAINER_NAME} sh -c "ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N '' &&
 cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys"

echo "Installing manager..."
docker exec -t ${CONTAINER_NAME} sh -c "cfy bootstrap ${MANAGER_BLUEPRINT_PATH} -i ${INPUTS_FILE_PATH} -v"

# configure cli for root user
docker exec -t ${CONTAINER_NAME} sh -c "cfy profiles use localhost -u ${CLOUDIFY_MANAGER_USERNAME} -p ${CLOUDIFY_MANAGER_PASSWORD} -t default_tenant"

echo "The Manager's IP is ${CONTAINER_IP}"

echo "Saving the image..."
docker commit -m "Install CFY Manager 4.2" $CONTAINER_NAME $IMAGE_PUB_NAME
docker stop $CONTAINER_NAME

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
