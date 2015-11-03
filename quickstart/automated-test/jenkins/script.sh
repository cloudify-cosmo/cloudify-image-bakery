#!/bin/bash

set -evx

#
# assumptions:
# - git installed
# - user is sudoer without password
# - project is cloned
# - ui system test project is cloned

. $CLOUDIFY_IMAGE_BAKERY/quickstart/automated-test/jenkins/provision.sh

install_node (){
    # assume node is installed
    if [ ! -f /usr/bin/node ];then
        echo "installing node"
        NODEJS_VERSION=0.10.35
        NODEJS_HOME=/opt/nodejs
        sudo mkdir -p $NODEJS_HOME
        sudo chown $USER:$USER $NODEJS_HOME
        curl --fail --silent http://nodejs.org/dist/v${NODEJS_VERSION}/node-v${NODEJS_VERSION}-linux-x64.tar.gz -o /tmp/nodejs.tar.gz
        tar -xzf /tmp/nodejs.tar.gz -C ${NODEJS_HOME} --strip-components=1
        sudo ln -s /opt/nodejs/bin/node /usr/bin/node
        sudo ln -s /opt/nodejs/bin/npm /usr/bin/npm

    else
        echo "node already installed"
    fi
}



run_tests(){
    sudo npm install -g grunt-cli phantomjs
    cd $TESTS_DIR
    npm install

    export PROTRACTOR_BASE_URL="http://10.10.1.10"
    export BROWSER_TYPE="phantomjs"
    grunt protract:quickstart || export TESTS_FAILED="true"
}

clean_env(){
    if [ "$CLEAN_ENV" = "true" ]; then
        vagrant box remove cloudify-virtualbox_${VERSION}-${PRERELEASE}-b${BUILD}.box || echo "failed to remove box, assume removed"
    else
        echo "skip clean env.."
    fi
    vagrant destroy -f || echo "vagrant destroy failed, assuming machine is not up"
}

install_node
clean_env

VAGRANTFILE_URL="http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/${VERSION}/${PRERELEASE}-RELEASE/Vagrantfile"
wget -O Vagrantfile $VAGRANTFILE_URL
vagrant up

export TESTS_FAILED="false"
run_tests

clean_env

if [ "$TESTS_FAILED" == "true" ];then
    echo "TESTS FAILED!!!"
    exit 1
fi