#!/bin/bash
set -e

base_dir=$(pwd)
svruser=yiiguo
node_num=$1
if [ -z "$node_num" ]; then
    echo "ERROR: node_num must be specified"
    exit 1
fi
server_file=$base_dir/yiiguo_test/node_multi/remote/servers
containers=$base_dir/yiiguo_test/node_multi/remote/containers
tendermint=$base_dir/build/tendermint
config=temp # home dir of all nodes

host_num=`cat ${server_file}|wc -l`
validator_nodes_per_host=$[$node_num/$host_num]
extra_nodes=$[$node_num - $host_num*$validator_nodes_per_host]
for host in `cat ${server_file}`; do
    servers[$i]=$host
    let i=$i+1
done
echo "servers: ${servers[@]}"

for idx in $(seq 0 $[${node_num}-1]); do
    hosts[$idx]=${servers[$[${idx}%${#servers[@]}]]}
    ports[$idx]=$[${port}+$[$idx/${#servers[@]}*2]]
done
echo "hosts: ${hosts[@]}"
echo "ports: ${ports[@]}"

# generate $node_num node-configs
echo "-------------generate node configs...-------------"
rm ${config}/* -rf
$tendermint testnet --v ${node_num} --o ${config} > /dev/null
echo "-------------ok!-------------"

# build image
echo "building tendermint image..."
docker build --label=tendermint --tag="tendermint/tendermint" -f DOCKER/Dockerfile .
echo "ok!"

# save image
echo "-------------save image...-------------"
docker save tendermint/tendermint -o tendermint.tar
echo "-------------ok!-------------"

# send image to servers
function send_image()
{
    host=$1
    scp ./tendermint.tar ${USER}@${host}:/home/${USER}/workspace/tendermint-node/multi-node/tendermint.tar
    ssh ${USER}@${host} "docker load -i /home/${USER}/workspace/tendermint-node/multi-node/tendermint.tar"
}
echo "-------------send images to servers...-------------" 
for host in ${servers[@]}; do
    echo "send to $host...\n"
    send_image $host & 
done
wait # wait all send processs done
echo "-------------ok!-------------"

# get id of each node
echo "-------------getting node ids...-------------"
for idx in $(seq 0 $[${node_num}-1]); do
    nodeids[idx]=`$tendermint show-node-id --home ${config}/node${idx}`
    echo "get node(${idx}) id: ${nodeids[${idx}]}"
done
echo "-------------ok!-------------"

# start each tendermint code
echo "-------------starting node...-------------"
if [ -f $containers ]; then
    rm $containers
fi
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
    --proxy-app=kvstore \
    --rpc.laddr=tcp://0.0.0.0:26657 \
    --p2p.persistent-peers='$peers'"
    # command: start docker on remote servers
    remote_cmd='if [ "$(docker ps -a | grep tendermint_'${idx}')" ]; then docker rm -f tendermint_'${idx}'; fi && '"\
    docker run -d \
    --user tmuser \
    --name tendermint_$idx \
    -p ${port}-${port_end}:26656-26657 \
    tendermint/tendermint \
    ${tmcmd}"
    ssh -n ${USER}@${host} "${remote_cmd}" &
    echo "${USER}@${host} tendermint_${idx}" >> $containers
done
wait
echo "-------------ok!-------------"