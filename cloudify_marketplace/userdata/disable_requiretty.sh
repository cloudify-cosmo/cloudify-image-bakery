#!/usr/bin/env bash

# disable requiretty
sed -i -e 's/^Defaults.*requiretty/# Defaults requiretty/g' /etc/sudoers