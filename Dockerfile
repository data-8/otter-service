FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y software-properties-common && \
    apt-get update && \
    add-apt-repository -y ppa:longsleep/golang-backports

RUN apt-get install -y python3 && \
    apt-get install -y python3-pip && \
    apt-get install -y curl && \
    apt-get install -y sqlite3 libsqlite3-dev && \
    apt-get install -y golang

# install golang to support sops(python-sops does nto work with GCP KMS)
RUN echo 'export PATH=$PATH:/root/go/bin' >> /root/.bashrc && \
    go install go.mozilla.org/sops/v3/cmd/sops@v3.7.1

COPY ./requirements/prod.txt /opt/gofer_service/prod.txt
RUN python3 -m pip install -r /opt/gofer_service/prod.txt
RUN python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps gofer-service==0.1.4

ENV DOCKER_CHANNEL stable
ENV DOCKER_VERSION 17.03.1-ce
ENV DOCKER_API_VERSION 1.27
RUN curl -fsSL "https://download.docker.com/linux/static/${DOCKER_CHANNEL}/x86_64/docker-${DOCKER_VERSION}.tgz" \
  | tar -xzC /usr/local/bin --strip=1 docker/docker

ADD https://github.com/sean-morris/materials-x19/archive/master.tar.gz /opt/
RUN tar -xzf /opt/master.tar.gz -C /opt && rm /opt/master.tar.gz && mv  /opt/materials-x19-master /opt/materials-x19

WORKDIR /opt

EXPOSE 10101
ENTRYPOINT ["gofer-service"]