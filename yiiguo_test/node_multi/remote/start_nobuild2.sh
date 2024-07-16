#!/bin/bash
set -e

groupId=$1
if [ -z "$groupId" ]; then
    echo "ERROR: groupId must be specified"
    exit 1
fi
port_head=$2
if [ -z "$port_head" ]; then
    echo "ERROR: port_head must be specified"
    exit 1
fi

base_dir=$(pwd)
svruser=yiiguo
server_file=$base_dir/yiiguo_test/node_multi/remote/servers
containers=$base_dir/yiiguo_test/node_multi/remote/containers
tendermint=$base_dir/build/tendermint
config=temp # dir of all nodes configs
image_name=tendermint_nobuild

node_num=`ls ${config}|wc -l` # 有多少个验证者就有多少个节点, 不考虑普通节点
host_num=`cat ${server_file}|wc -l`
validator_nodes_per_host=$[$node_num/$host_num]
extra_nodes=$[$node_num - $host_num*$validator_nodes_per_host]
for host in `cat ${server_file}`; do
    servers[$i]=$host
    let i=$i+1
done
echo "servers: ${servers[@]}"
echo "validator_nodes_per_host: ${validator_nodes_per_host}"
echo "extra_nodes: ${extra_nodes}"

# each node has a host and a port
port=$port_head
for idx in $(seq 0 $[${node_num}-1]); do
    hosts[$idx]=${servers[$[${idx}%${#servers[@]}]]}
    ports[$idx]=$[${port}+$[$idx/${#servers[@]}*2]] # multi 2 because each node needs two ports 26656 and 26657
done
echo "hosts: ${hosts[@]}"
echo "ports: ${ports[@]}"

# get id of each node
echo "-------------getting node ids...-------------"
for idx in $(seq 0 $[${node_num}-1]); do
    nodeids[idx]=`$tendermint show-node-id --home ${config}/node${idx}`
    echo "get node(${idx}) id: ${nodeids[${idx}]}"
done
echo "-------------ok!-------------"

# start each tendermint code
echo "-------------starting node...-------------"
for idx in $(seq 0 $[${node_num}-1]); do
    echo "staring node(${idx})..."
    host=${hosts[$idx]}
    port=${ports[$idx]}
    port_end=$[${port}+1]
    node_home=/tendermint/node${idx}
    peers=""
    for idx2 in $(seq 0 $[${node_num}-1]); do
        if [ $idx2 -ne $idx ]; then
            if [ -n "$peers" ]; then
                peers=$peers","
            fi
            peers=$peers"${nodeids[${idx2}]}@${hosts[$idx2]}:${ports[$idx2]}"
        fi
    done
    # command: start tendermint 
    tmcmd="start \
    --home ${node_home} \
    --consensus.create-empty-blocks=false \
    --consensus.create-empty-blocks-interval='500s' \
    --proxy-app=kvstore \
    --rpc.laddr=tcp://0.0.0.0:26657 \
    --p2p.persistent-peers='$peers'"
    # command: start docker on remote servers
    remote_cmd='if [ "$(docker ps -a | grep tendermint_'${groupId}_${idx}')" ]; then docker rm -f tendermint_'${groupId}_${idx}'; fi && '"\
    docker run -d \
    --user root \
    --name tendermint_${groupId}_${idx} \
    -p ${port}-${port_end}:26656-26657 \
    tendermint/$image_name \
    ${tmcmd}"
    ssh -n ${USER}@${host} "${remote_cmd}" &
    echo "${USER}@${host} tendermint_${groupId}_${idx} ${groupId}" >> $containers
done
wait
echo "-------------ok!-------------"