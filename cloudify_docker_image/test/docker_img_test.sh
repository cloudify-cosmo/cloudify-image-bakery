#!/bin/bash

function validate(){
    if ! which docker 1> /dev/null || ! which docker-compose 1> /dev/null ; then
        echo "Please install docker and docker-compose"
        exit 1
    fi
}

function upload_manager(){
    echo "Uploading Cloudify manager ..."
    docker-compose up -d
    sleep 5
}

function put_manager_in_sanity_mode(){
    echo "Placing manager in sanity"
    docker-compose exec -T cloudify_img touch /opt/manager/sanity_mode
    echo "Restarting rest service and waiting it to come back"
    docker-compose exec -T systemctl restart cloudify-restservice
    sleep 15s
    echo "Manager back and in sanity mode"
}

function test_manager(){
    echo "Testing Cloudify manager ..."
    ip_address=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTAINER_NAME)
    echo "ip_address=$ip_address"
    echo "docker-compose exec -T cloudify_img cfy_manager sanity-check --private-ip $ip_address"
    docker-compose exec -T cloudify_img cfy_manager sanity-check --private-ip $ip_address
    if [ $? -ne 0 ]; then
        echo "cfy_manager sanity-check failed"
        docker-compose exec -T cloudify_img cat /var/log/cloudify/manager/cfy_manager.log
        remove_manager
        exit 1
    fi
}

function remove_manager(){
    echo "Removing Cloudify manager ..."
    docker-compose down
}


validate
upload_manager
put_manager_in_sanity_mode
test_manager
remove_manager
