#!/bin/bash

sudo yum remove -y gcc
sudo yum autoremove -y
sudo yum clean -y all
sudo rm -rf /tmp/*