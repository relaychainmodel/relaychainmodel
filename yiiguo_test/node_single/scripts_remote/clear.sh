#!/bin/bash

ssh yiiguo@10.21.4.37 "pkill -f 'tendermint start --home .'"

ssh yiiguo@10.21.4.37 "cd /home/yiiguo/workspace/tendermint-node/single_node && \
rm -rf ./config && \
rm -rf ./data"