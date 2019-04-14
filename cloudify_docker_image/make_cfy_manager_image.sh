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

function generate_config_yaml()
{
    case  $IMAGE_TYPE  in
        "ALL_IN_ONE")
            echo  "manager:
  private_ip: ${CONTAINER_IP}
  public_ip: ${CONTAINER_IP}
  set_manager_ip_on_boot: true
  security:
    admin_password: admin
  monitoring_install: &monitoring_install
    skip_installation: false" > config.yaml
            IMAGE_PUB_NAME="docker-cfy-manager"
            declare -a IMAGE_TAGS=( "latest" "cloudify-manager-$VERSION-$PRERELEASE" )
            ;;
        "POSTGRESQL")
            echo  "manager:
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
    - 'database_service'" > config.yaml
            IMAGE_PUB_NAME="docker-cfy-manager-postgresql"
            declare -a IMAGE_TAGS=( "latest" "cloudify-manager-postgresql-$VERSION-$PRERELEASE" )
            ;;
        "RABBITMQ")
            echo  "manager:
  private_ip: ${CONTAINER_IP}
  public_ip: ${CONTAINER_IP}
  set_manager_ip_on_boot: true
  security:
    admin_password: admin
  monitoring_install: &monitoring_install
    skip_installation: false
  services_to_install:
    - 'queue_service'" > config.yaml
            IMAGE_PUB_NAME="docker-cfy-manager-rabbitmq"
            declare -a IMAGE_TAGS=( "latest" "cloudify-manager-rabbitmq-$VERSION-$PRERELEASE" )
            ;;
        "MANAGER_WORKER")
            echo  "manager:
  private_ip: ${CONTAINER_IP}
  public_ip: ${CONTAINER_IP}
  set_manager_ip_on_boot: true
  security:
    admin_password: admin
  monitoring_install: &monitoring_install
    skip_installation: false
  services_to_install:
    - 'manager_service'" > config.yaml
            IMAGE_PUB_NAME="docker-cfy-manager-worker"
            declare -a IMAGE_TAGS=( "latest" "cloudify-manager-worker-$VERSION-$PRERELEASE" )
            ;;
        *)
    esac
}

echo "The config.yaml:"
cat config.yaml

function upload_image_to_registry
{
	docker login -u="${DOCKER_BUILD_ID}" -p="${DOCKER_BUILD_PASSWORD}"
	for i in "${IMAGE_TAGS[@]}"
	do
		docker tag $IMAGE_PUB_NAME ${DOCKER_ORGANIZATION}/${DOCKER_REPO}:$i
		set +e
		echo "Removing the ${DOCKER_ORGANIZATION}/${DOCKER_REPO}:$i image from registry"
		TOKEN=$(curl -s -H "Content-Type: application/json" -X POST -d '{"username": "'${DOCKER_ID_USER}'", "password": "'${DOCKER_ID_PASSWORD}'"}' https://hub.docker.com/v2/users/login/ | jq -r .token)
		curl -X DELETE  -H "Authorization: JWT ${TOKEN}" https://hub.docker.com/v2/repositories/${DOCKER_ORGANIZATION}/${DOCKER_REPO}/tags/${i}/
		set -e
		echo "Uploading the ${DOCKER_ORGANIZATION}/${DOCKER_REPO}:$i image"
		docker push ${DOCKER_ORGANIZATION}/${DOCKER_REPO}:$i
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

generate_config_yaml

echo "Installing cfy..."
docker exec -t $CONTAINER_NAME sh -c "curl $CFY_RPM_URL -o ~/$CFY_RPM &&
 rpm -i ~/$CFY_RPM &&
 rm -f ~/$CFY_RPM"

docker cp config.yaml ${CONTAINER_NAME}:${MANAGER_CONFIG_LOCATION}

echo "Installing manager..."
docker exec -t ${CONTAINER_NAME} sh -c "cfy_manager install --only-install"
docker exec -t ${CONTAINER_NAME} sh -c "echo 'docker' > /opt/cfy/image.info"

echo "Saving the image..."
docker commit -m "Install CFY manager" $CONTAINER_NAME $IMAGE_PUB_NAME
for i in "${IMAGE_TAGS[@]}"
do
	docker tag $IMAGE_PUB_NAME ${DOCKER_ORGANIZATION}/${DOCKER_REPO}:$i
done

echo "Removing the used container..."
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME
