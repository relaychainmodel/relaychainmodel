# stage 1 Generate Tendermint Binary
FROM golang:1.16-alpine as builder
RUN apk update && \
    apk upgrade && \
    apk --no-cache add make && \
    go env -w GO111MODULE=on && go env -w GOPROXY=https://goproxy.io,direct
COPY / /tendermint
WORKDIR /tendermint
ENV HTTP_PROXY=http://10.21.4.204:7890 HTTPS_PROXY=http://10.21.4.204:7890
RUN make build-linux

# stage 2
FROM golang:1.15-alpine
LABEL maintainer="hello@tendermint.com"
COPY temp /tendermint

# Tendermint will be looking for the genesis file in /tendermint/config/genesis.json
# (unless you change `genesis_file` in config.toml). You can put your config.toml and
# private validator file into /tendermint/config.
#
# The /tendermint/data dir is used by tendermint to store state.
ENV TMHOME /tendermint

# OS environment setup
# Set user right away for determinism, create directory for persistence and give our user ownership
# jq and curl used for extracting `pub_key` from private validator while
# deploying tendermint with Kubernetes. It is nice to have bash so the users
# could execute bash commands.
RUN apk update && \
    apk upgrade && \
    apk --no-cache add curl jq bash && \
    addgroup tmuser && \
    adduser -S -G tmuser tmuser -h "$TMHOME" && \
    chown -R tmuser:tmuser "$TMHOME"

# Run the container with tmuser by default. (UID=100, GID=1000)
USER tmuser

WORKDIR $TMHOME

# p2p, rpc and prometheus port
# specify it in the command 'docker run ...'
# EXPOSE 26650-26680

STOPSIGNAL SIGTERM

COPY --from=builder /tendermint/build/tendermint /usr/bin/tendermint

# You can overwrite these before the first run to influence
# config.json and genesis.json. Additionally, you can override
# CMD to add parameters to `tendermint node`.
ENV PROXY_APP=kvstore MONIKER=dockernode CHAIN_ID=dockerchain

COPY ./DOCKER/docker-entrypoint.sh /usr/local/bin/

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]

# # Expose the data directory as a volume since there's mutable state in there
# VOLUME [ "$TMHOME" ]

