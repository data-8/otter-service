FROM ubuntu:20.04
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y python3 && \
    apt-get install -y python3-pip && \
    apt-get install -y curl && \
    apt-get install -y sqlite3 libsqlite3-dev

COPY . /opt/gofer_service/
RUN python3 -m pip install -r /opt/gofer_service/requirements/prod.txt
RUN python3 -m pip install /opt/gofer_service/

ENV DOCKER_CHANNEL stable
ENV DOCKER_VERSION 17.03.1-ce
ENV DOCKER_API_VERSION 1.27
RUN curl -fsSL "https://download.docker.com/linux/static/${DOCKER_CHANNEL}/x86_64/docker-${DOCKER_VERSION}.tgz" \
  | tar -xzC /usr/local/bin --strip=1 docker/docker

ADD https://github.com/sean-morris/materials-x19/archive/master.tar.gz /opt/
RUN tar -xzf /opt/master.tar.gz -C /opt && rm /opt/master.tar.gz && mv  /opt/materials-x19-master /opt/materials-x19

WORKDIR /opt

EXPOSE 10101
ENTRYPOINT ["python3", "/opt/gofer_service/src/gofer_service/gofer_nb.py"]