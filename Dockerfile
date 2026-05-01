FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive
ARG OTTER_SERVICE_VERSION

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y python3 python3-pip curl

# Install Go directly from upstream to avoid flaky Launchpad PPA network calls
RUN curl -fsSL https://go.dev/dl/go1.21.13.linux-amd64.tar.gz | tar -C /usr/local -xz
ENV PATH="/usr/local/go/bin:/root/go/bin:$PATH"

# install sops via go (python-sops does not work with GCP KMS)
RUN go install go.mozilla.org/sops/v3/cmd/sops@v3.7.3

COPY ./requirements/requirements.txt /opt/otter-service/requirements.txt
RUN python3 -m pip install -r /opt/otter-service/requirements.txt
COPY . /opt/otter-service-src/
RUN if [ -n "${OTTER_SERVICE_VERSION}" ]; then \
      python3 -m pip install otter-service==${OTTER_SERVICE_VERSION}; \
    else \
      python3 -m pip install /opt/otter-service-src/; \
    fi

# install docker cli
ENV DOCKER_VERSION 5:24.0.4-1~ubuntu.22.04~jammy
RUN apt-get update
RUN apt-get install -y \
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