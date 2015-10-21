#!/usr/bin/env bash

# disable selinux
sudo setenforce 0
sudo sed -ri 's/SELINUX=.+/SELINUX=disabled/' /etc/selinux/config

