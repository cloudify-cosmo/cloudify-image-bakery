FROM circleci/python:2.7.14

ENV TINI_VERSION v0.18.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /sbin/tini
RUN sudo chmod +x /sbin/tini
ENTRYPOINT ["/sbin/tini", "--"]
