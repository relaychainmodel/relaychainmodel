#!/bin/bash

echo "clearing..."
sh ./yiiguo_test/node_single/scripts_remote/clear.sh

echo "starting..."
ssh yiiguo@10.21.4.37 "cd /home/yiiguo/workspace/tendermint-node/single_node && \
./tendermint init validator --home . && \
eval 'nohup ./tendermint start --home . --log-level=info --consensus.create-empty-blocks=false --rpc.laddr=tcp://0.0.0.0:26657 --proxy-app=kvstore >./tendermint.log  2>&1 &'"

echo "finished!"

# ssh yiiguo@10.21.4.37 << EOF
# pkill -f 'tendermint start --home .'
# cd /home/yiiguo/workspace/tendermint-node/single_node
# rm -rf ./config
# rm -rf ./data
# ./tendermint init validator --home . 
# $(nohup ./tendermint start --home . --log-level=info --consensus.create-empty-blocks=false --proxy-app=kvstore 2>&1 >./tendermint.log &)
# EOF