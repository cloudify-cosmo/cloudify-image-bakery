#!/bin/bash

function install_prereqs
{
  echo installing prerequisites
  [[ $EUID -ne 0 ]] && SUDO=$(which sudo) || SUDO=""

  $SUDO yum install -y git gcc python-devel
  curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | $SUDO python
  $SUDO pip install virtualenv
}

function create_virtualenv
{
  echo creating cloudify virtualenv
  virtualenv $CFY_VENV
}

function install_cli
{
  $CFY_VENV/bin/pip install https://github.com/cloudify-cosmo/cloudify-cli/archive/$CORE_TAG_NAME.zip \
    -r https://raw.githubusercontent.com/cloudify-cosmo/cloudify-cli/$CORE_TAG_NAME/dev-requirements.txt
}

function init_cfy_workdir
{
  mkdir -p $CFY_ENV
  pushd $CFY_ENV
  $CFY_VENV/bin/cfy init
  popd
}

function get_manager_blueprints
{
  echo "Retrieving Manager Blueprints"
  mkdir -p $CFY_ENV/cloudify-manager-blueprints
  dest=$(mktemp --suffix=.tar.gz)
  curl --fail -L https://github.com/cloudify-cosmo/cloudify-manager-blueprints/archive/$CORE_TAG_NAME.tar.gz -o $dest
  tar -zxf $dest -C $CFY_ENV/cloudify-manager-blueprints --strip-components=1
}

function generate_keys
{
  # generate public/private key pair and add to authorized_keys
  ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ''
  cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
}

function bootstrap
{
  pushd $CFY_ENV
  echo "bootstrapping..."
  # bootstrap the manager locally
  PATH=$CFY_VENV/bin:PATH $CFY_VENV/bin/cfy bootstrap -v --install-plugins \
      -p cloudify-manager-blueprints/simple-manager-blueprint.yaml \
      -i "public_ip=127.0.0.1; \
          private_ip=127.0.0.1; \
          ssh_user=${USER}; \
          ssh_key_filename=/home/${USER}/.ssh/id_rsa"
  if [ "$?" -ne "0" ]; then
    echo "Bootstrap failed, stoping provision."
    exit 1
  fi
  echo "bootstrap done."
  popd
}

CFY_VENV="$HOME/cfy"
CFY_ENV="$HOME/cloudify"
if [ -z "$CORE_TAG_NAME" ]; then
  echo "### Building from master branch ###"
  CORE_TAG_NAME="master"
fi

install_prereqs
create_virtualenv
install_cli
init_cfy_workdir
get_manager_blueprints
generate_keys
bootstrap
