rm -rf ./yiiguo_test/node_single/* && tendermint init validator --home ./yiiguo_test/node_single

tendermint show_node_id --home ./yiiguo_test/node_single

nohup ./build/tendermint start --home ./yiiguo_test/node_single --consensus.create-empty-blocks=false --proxy-app=kvstore 2>&1 > ./yiiguo_test/node_single/tendermint.log &

nohup ~/workspace/tendermint-node/test/tendermint start --home ~/workspace/tendermint-node/test/ --proxy-app=kvstore \
--p2p.persistent-peers="\
8c93323fb489d460f93e0ab71b50adc4a8408185@10.21.4.36:26656,\
210a7e698283c159ebf2f1d138ec6d9808c1e81e@10.21.4.37:26656,\
5e6fcce0bdec20814e911b79047e79aed2b78576@10.21.4.38:26656,\
19d1e7a68fc97a25adba2ba129e4b803ea6cc7f8@10.21.4.39:26656" 2>&1 > tendermint.log &

nohup ~/workspace/tendermint-node/test/tendermint start --home ~/workspace/tendermint-node/test/node0 --proxy-app=kvstore \
--p2p.persistent-peers="\
210a7e698283c159ebf2f1d138ec6d9808c1e81e@10.21.4.37:26656,\
5e6fcce0bdec20814e911b79047e79aed2b78576@10.21.4.38:26656,\
19d1e7a68fc97a25adba2ba129e4b803ea6cc7f8@10.21.4.39:26656" 2>&1 > tendermint.log &

nohup ~/workspace/tendermint-node/test/tendermint start --home ~/workspace/tendermint-node/test/node1 --proxy-app=kvstore \
--p2p.persistent-peers="\
8c93323fb489d460f93e0ab71b50adc4a8408185@10.21.4.36:26656,\
5e6fcce0bdec20814e911b79047e79aed2b78576@10.21.4.38:26656,\
19d1e7a68fc97a25adba2ba129e4b803ea6cc7f8@10.21.4.39:26656" 2>&1 > tendermint.log &

nohup ~/workspace/tendermint-node/test/tendermint start --home ~/workspace/tendermint-node/test/node2 --proxy-app=kvstore \
--p2p.persistent-peers="\
8c93323fb489d460f93e0ab71b50adc4a8408185@10.21.4.36:26656,\
210a7e698283c159ebf2f1d138ec6d9808c1e81e@10.21.4.37:26656,\
19d1e7a68fc97a25adba2ba129e4b803ea6cc7f8@10.21.4.39:26656" 2>&1 > tendermint.log &

nohup ~/workspace/tendermint-node/test/tendermint start --home ~/workspace/tendermint-node/test/node3 --proxy-app=kvstore \
--p2p.persistent-peers="\
8c93323fb489d460f93e0ab71b50adc4a8408185@10.21.4.36:26656,\
210a7e698283c159ebf2f1d138ec6d9808c1e81e@10.21.4.37:26656,\
5e6fcce0bdec20814e911b79047e79aed2b78576@10.21.4.38:26656" 2>&1 > tendermint.log &


cat ./yiiguo_test/node_single/tendermint.log | grep "yiiguo txmempool metrics" | tail -n 10

cat ./yiiguo_test/node_single/tendermint.log | grep "yiiguo block metrics" | tail -n 10

cat ./yiiguo_test/node_single/tendermint.log | grep "yiiguo transaction metrics" | tail -n 10

docker rmi $(docker images | grep '<none>' | tr -s ' '| cut -d ' ' -f 3)

docker rm -f $(docker ps -a | grep tendermint | tr -s ' '| cut -d ' ' -f 1 )

firewall-cmd --zone=public --add-port=26400-26600/tcp --permanent && firewall-cmd --reload