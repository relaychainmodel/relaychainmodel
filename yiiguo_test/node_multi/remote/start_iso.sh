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
port=26656
for idx in $(seq 0 $[${node_num}-1]); do
    hosts[$idx]=${servers[$[${idx}%${#servers[@]}]]}
    ports[$idx]=$[${port}+$[$idx/${#servers[@]}*2]]
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
if [ -f $containers ]; then
    rm $containers
fi
for idx in $(seq 0 $[${node_num}-1]); do
    echo "staring node(${idx})..."
    host=${hosts[$idx]}
    port=${ports[$idx]}
    port_end=$[${port}+1]
    node_home=/tendermint/temp/node${idx}
    peers=""
    for idx2 in $(seq 0 $[${node_num}-1]); do
        if [ $idx2 -ne $idx ]; then
            if [ -n "$peers" ]; then
                peers=$peers","
            fi
            peers=$peers"${nodeids[${idx2}]}@${hosts[$idx2]}:${ports[$idx2]}"
        fi
    done
    container_name=tendermint_isolate_$idx
    tmcmd="/tendermint/tendermint start \
        --home ${node_home} \
        --consensus.create-empty-blocks=false \
        --proxy-app=kvstore \
        --rpc.laddr=tcp://0.0.0.0:26657 \
        --p2p.persistent-peers='$peers' \
        >${node_home}/tendermint.log 2>&1"
    cmd_rm='if [ "$(docker ps -a | grep '$container_name')" ]; then docker rm -f '$container_name'; fi'
    cmd_cd="cd /home/${USER}/workspace/tendermint-node/multi-node/"
    cmd_run="docker run -itd --user tmuser --name $container_name -p ${port}-${port_end}:26656-26657 tendermint/tendermint_isolate /bin/bash"
    cmd_cp_temp="docker cp temp $container_name:/tendermint/"
    cmd_cp_tm="docker cp tendermint $container_name:/tendermint/"
    cmd_auth="docker exec -itd --user root $container_name bash -c 'chown -R tmuser:tmuser /tendermint'"
    cmd_exec='docker exec -itd '$container_name' bash -c "'$tmcmd'"'
    echo $cmd_exec
    ssh -n ${USER}@${host} "$cmd_cd && $cmd_rm && $cmd_run && $cmd_cp_temp && $cmd_cp_tm && $cmd_auth && $cmd_exec"
    
    echo "${USER}@${host} tendermint_${idx}" >> $containers
done
wait
echo "-------------ok!-------------"