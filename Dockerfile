FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
ARG GIT_ACCESS_TOKEN

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
    go install go.mozilla.org/sops/v3/cmd/sops@v3.7.3

COPY ./requirements/prod.txt /opt/gofer_service/prod.txt
RUN python3 -m pip install -r /opt/gofer_service/prod.txt
RUN python3 -m pip install gofer-service

ENV DOCKER_CHANNEL stable
ENV DOCKER_VERSION 17.03.1-ce
ENV DOCKER_API_VERSION 1.27
RUN curl -fsSL "https://download.docker.com/linux/static/${DOCKER_CHANNEL}/x86_64/docker-${DOCKER_VERSION}.tgz" \
  | tar -xzC /usr/local/bin --strip=1 docker/docker

ADD https://${GIT_ACCESS_TOKEN}:@github.com/data-8/materials-x22-private/archive/main.tar.gz /opt/
RUN tar -xzf /opt/main.tar.gz -C /opt && rm /opt/main.tar.gz && mv  /opt/materials-x22-private-main /opt/materials-x22-private

WORKDIR /opt

EXPOSE 10101
ENTRYPOINT ["gofer-service"]