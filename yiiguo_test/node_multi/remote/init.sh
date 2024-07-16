#!/bin/bash
set -e

node_num=$1
if [ -z "$node_num" ]; then
    echo "ERROR: node_num must be specified"
    exit 1
fi

base_dir=$(pwd)
svruser=yiiguo
server_file=$base_dir/yiiguo_test/node_multi/remote/servers
config=temp # home dir of all nodes
image_name=tendermint_nobuild

# build new tendermint
make build

tendermint=$base_dir/build/tendermint

host_num=`cat ${server_file}|wc -l`
validator_nodes_per_host=$[$node_num/$host_num]
extra_nodes=$[$node_num - $host_num*$validator_nodes_per_host]
for host in `cat ${server_file}`; do
    servers[$i]=$host
    let i=$i+1
done
echo "servers: ${servers[@]}"

# generate $node_num node-configs
echo "-------------generate node configs...-------------"
rm -f ${config}/* -r
$tendermint testnet --v ${node_num} --o ${config} > /dev/null
echo "-------------ok!-------------"

# build image
echo "building tendermint image..."
docker build --label=tendermint --tag="tendermint/$image_name" -f DOCKER/Dockerfile.nobuild .
echo "ok!"

# save image
echo "-------------save image...-------------"
docker save tendermint/$image_name -o $image_name.tar
echo "-------------ok!-------------"

# send image to servers
function send_image()
{
    host=$1
    dirpath=/home/${USER}/workspace/tendermint-node/multi-node
    ssh ${USER}@${host} "if [ ! -d \"${dirpath}/test\" ]; then mkdir -p ${dirpath}; fi"
    scp ./$image_name.tar ${USER}@${host}:${dirpath}/$image_name.tar
    ssh ${USER}@${host} "docker load -i ${dirpath}/$image_name.tar"
}
echo "-------------send images to servers...-------------" 
for host in ${servers[@]}; do
    echo "send to $host...\n"
    send_image $host & 
done
wait # wait all send processs done
echo "-------------ok!-------------"