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

function test_manager(){
    echo "Testing Cloudify manager ..."
    ip_address=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTAINER_NAME)
    echo "ip_address=$ip_address"
    echo "docker-compose exec -T cloudify_img cfy_manager sanity-check --private-ip $ip_address"
    docker-compose exec -T cloudify_img cfy_manager sanity-check --private-ip $ip_address
    if [ $? -ne 0 ]; then
        echo "cfy_manager sanity-check failed"
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
test_manager
remove_manager