FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y software-properties-common && \
    apt-get update && \
    add-apt-repository -y ppa:longsleep/golang-backports

RUN apt-get install -y python3 && \
    apt-get install -y python3-pip && \
    apt-get install -y curl && \
    apt-get install -y golang


# install golang to support sops(python-sops does nto work with GCP KMS)
RUN echo 'export PATH=$PATH:/root/go/bin' >> /root/.bashrc && \
    go install go.mozilla.org/sops/v3/cmd/sops@v3.7.3

COPY ./requirements/prod.txt /opt/otter-service/prod.txt
RUN python3 -m pip install -r /opt/otter-service/prod.txt
RUN python3 -m pip install otter-service

# install docker cli
ENV DOCKER_VERSION 5:24.0.4-1~ubuntu.22.04~jammy
RUN apt-get update
RUN apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update
RUN apt-get -y install docker-ce-cli=${DOCKER_VERSION}

WORKDIR /opt

EXPOSE 10101
ENTRYPOINT ["otter_service"]