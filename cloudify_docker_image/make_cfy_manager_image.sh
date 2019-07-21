#!/usr/bin/env bash

set -eu

if [ $# -eq 0 ]
  then
    echo "No arguments supplied. Please supply the CFY RPM URL as the first argument."
    exit
fi
# argument 1 is RPM URL
# argument 2 is image-type, one of: all_in_one, postgresql, rabbitmq, manager_worker
CFY_RPM_URL=$1
IMAGE_TYPE=$2
CFY_RPM="cloudify-manager-install.rpm"
CONTAINER_NAME="cfy-manager"
BASE_IMAGE="$(docker images | grep latest-centos7-base-image | awk '{print $3}')"

DOCKER_RUN_FLAGS="--name ${CONTAINER_NAME} -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run
 --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN"
MANAGER_CONFIG_LOCATION="/etc/cloudify"

function upload_image_to_registry
{
	docker login -u="${DOCKER_BUILD_ID}" -p="${DOCKER_BUILD_PASSWORD}"
	for i in "${IMAGE_TAGS[@]}"
	do
		docker tag $IMAGE_PUB_NAME ${DOCKER_ORGANIZATION}/${DOCKER_REPO}-${IMAGE_DOCKER_HUB_NAME}:$i
		set +e
		echo "Removing the ${DOCKER_ORGANIZATION}/${DOCKER_REPO}-${IMAGE_DOCKER_HUB_NAME}:$i image from registry"
		TOKEN=$(curl -s -H "Content-Type: application/json" -X POST -d '{"username": "'${DOCKER_ID_USER}'", "password": "'${DOCKER_ID_PASSWORD}'"}' https://hub.docker.com/v2/users/login/ | jq -r .token)
		curl -X DELETE  -H "Authorization: JWT ${TOKEN}" https://hub.docker.com/v2/repositories/${DOCKER_ORGANIZATION}/${DOCKER_REPO}-${IMAGE_DOCKER_HUB_NAME}/tags/${i}/
		set -e
		echo "Uploading the ${DOCKER_ORGANIZATION}/${DOCKER_REPO}-${IMAGE_DOCKER_HUB_NAME}:$i image"
		docker push ${DOCKER_ORGANIZATION}/${DOCKER_REPO}-${IMAGE_DOCKER_HUB_NAME}:$i
	done

	docker logout
}
function get_repo
{
	if [[ $CFY_RPM_URL =~ "community" ]];then
	    DOCKER_REPO="community"
	else
	    DOCKER_REPO="premium"
	fi
}

get_repo

echo "Creating container..."
docker run ${DOCKER_RUN_FLAGS} ${BASE_IMAGE}
CONTAINER_IP=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${CONTAINER_NAME})

case $IMAGE_TYPE in
"manager-aio")
  echo "Setting config.yaml to install manager-aio"
  echo "
manager:
  private_ip: ${CONTAINER_IP}
  public_ip: ${CONTAINER_IP}
  set_manager_ip_on_boot: true
  security:
    admin_password: admin
monitoring_install: &monitoring_install
  skip_installation: false
  " > config.yaml
  IMAGE_PUB_NAME="docker-cfy-manager-aio"
  IMAGE_DOCKER_HUB_NAME="cloudify-manager-aio"
  declare -a IMAGE_TAGS=( "latest" "$VERSION-$PRERELEASE" )
  ;;
"postgresql")
  echo "Setting config.yaml to install postgresql"
  echo "
manager:
  private_ip: ${CONTAINER_IP}
  public_ip: ${CONTAINER_IP}
  set_manager_ip_on_boot: true
  security:
    admin_password: admin
monitoring_install: &monitoring_install
  skip_installation: false
postgresql_server:
  enable_remote_connections: true
  postgres_password: admin
  ssl_enabled: true
services_to_install:
  - 'database_service'
  " > config.yaml
  IMAGE_PUB_NAME="docker-cfy-postgresql"
  IMAGE_DOCKER_HUB_NAME="cloudify-postgresql"
  declare -a IMAGE_TAGS=( "latest" "$VERSION-$PRERELEASE" )
  ;;
"rabbitmq")
  echo "Setting config.yaml to install rabbitmq"
  echo "
manager:
  private_ip: ${CONTAINER_IP}
  public_ip: ${CONTAINER_IP}
  set_manager_ip_on_boot: true
  security:
    admin_password: admin
monitoring_install: &monitoring_install
  skip_installation: false
services_to_install:
  - 'queue_service'
  " > config.yaml
  IMAGE_PUB_NAME="docker-cfy-rabbitmq"
  IMAGE_DOCKER_HUB_NAME="cloudify-rabbitmq"
  declare -a IMAGE_TAGS=( "latest" "$VERSION-$PRERELEASE" )
  ;;
"manager-worker")
  echo "Setting config.yaml to install manager-worker"
  echo "
manager:
  private_ip: ${CONTAINER_IP}
  public_ip: ${CONTAINER_IP}
  set_manager_ip_on_boot: true
  security:
    admin_password: admin
monitoring_install: &monitoring_install
  skip_installation: false
services_to_install:
  - 'manager_service'
  " > config.yaml
  IMAGE_PUB_NAME="docker-cfy-manager-worker"
  IMAGE_DOCKER_HUB_NAME="cloudify-manager-worker"
  declare -a IMAGE_TAGS=( "latest" "$VERSION-$PRERELEASE" )
  ;;
*)
esac

echo "Installing cfy..."
docker exec -t $CONTAINER_NAME sh -c "curl $CFY_RPM_URL -o ~/$CFY_RPM &&
 rpm -i ~/$CFY_RPM &&
 rm -f ~/$CFY_RPM"

docker cp config.yaml ${CONTAINER_NAME}:${MANAGER_CONFIG_LOCATION}

# This is required for k8s installations
docker cp k8s_copy_and_install.sh ${CONTAINER_NAME}:${MANAGER_CONFIG_LOCATION}

echo "Installing manager..."
if [[ "$IMAGE_TYPE" == "manager-aio" ]]; then
    docker exec -t ${CONTAINER_NAME} sh -c "cfy_manager install"
else
    docker exec -t ${CONTAINER_NAME} sh -c "cfy_manager install --only-install"
fi
# If we are not installing a manager we won't have that directory and we need the image.info for the usage-collector
docker exec -t ${CONTAINER_NAME} sh -c "mkdir -p /opt/cfy/"
docker exec -t ${CONTAINER_NAME} sh -c "echo 'docker' > /opt/cfy/image.info"

echo "Saving the image..."
docker commit -m "Install Cloudify relevant components" $CONTAINER_NAME $IMAGE_PUB_NAME

docker tag $IMAGE_PUB_NAME ${DOCKER_ORGANIZATION}/${DOCKER_REPO}-${IMAGE_DOCKER_HUB_NAME}:latest

echo "Removing the used container..."
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME
