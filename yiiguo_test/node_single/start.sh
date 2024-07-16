#!/bin/bash

sh ./yiiguo_test/node_single/init.sh
nohup ./build/tendermint start --home ./yiiguo_test/node_single/node --log-level=info --rpc.laddr=tcp://0.0.0.0:26657 --consensus.create-empty-blocks=false --proxy-app=kvstore > ./yiiguo_test/node_single/tendermint.log 2>&1 &