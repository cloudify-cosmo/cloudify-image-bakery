FROM centos:7

# This should save some time for the installations of all these programs
RUN yum install -y deltarpm
RUN yum install -y epel-release
RUN yum install -y initscripts sudo openssh-server systemd-sysv openssl-1.0.2k \
    libselinux-utils logrotate python-setuptools \
    python-backports python-backports-ssl_match_hostname which cronie
RUN ssh-keygen -A

ENV container=docker

RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
rm -f /lib/systemd/system/multi-user.target.wants/*;\
rm -f /etc/systemd/system/*.wants/*;\
rm -f /lib/systemd/system/local-fs.target.wants/*; \
rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
rm -f /lib/systemd/system/basic.target.wants/*;\
rm -f /lib/systemd/system/anaconda.target.wants/*;

EXPOSE 22 80 443 5671 5672 53333

# Should help to stop the container gracfully
STOPSIGNAL SIGRTMIN+3

RUN systemctl set-default multi-user.target ; systemctl enable crond
VOLUME [ "/sys/fs/cgroup" ]
CMD ["/bin/bash", "-c", "exec /sbin/init --log-target=journal 3>&1"]
