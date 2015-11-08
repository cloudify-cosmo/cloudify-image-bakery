#!/bin/bash -e
[[ $EUID -ne 0 ]] && SUDO=$(which sudo) || SUDO=""

$SUDO rm -rf ~/.ssh/* /tmp/* ~/cfy ~/cloudify ~/blueprint
$SUDO yum clean all
