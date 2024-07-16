#!/bin/bash
# clear containers on all servers
# 
# desc:
# sh yiiguo_test/node_multi/remote/get_log.sh log_dir group_id
# log_dir is optional, default: yiiguo_test/node_multi/remote/log
# 
# demo:
# sh yiiguo_test/node_multi/remote/get_log.sh 5
# sh yiiguo_test/node_multi/remote/get_log.sh yiiguo_test/node_multi/remote/log 5

set -e

base_dir=$(pwd)
containers=$base_dir/yiiguo_test/node_multi/remote/containers
log=$base_dir/yiiguo_test/node_multi/remote/log
if [ "$1" ]; then
    if [ -d "$1" ]; then
        log=$1
        groupId=$2
        if [ -z "$groupId" ]; then echo "ERROR: need groupId"; exit 1; fi
    else
        groupId=$1
    fi
else
    echo "ERROR: need groupId"
    exit 1
fi
echo "logdir: $log"


while read info; do
    if [ -n "$info" ]; then
        remote_ip=$(echo $info | cut -d ' ' -f 1)
        container=$(echo $info | cut -d ' ' -f 2)
        group_id=$(echo $info | cut -d ' ' -f 3)
        if [ "$group_id" != "$groupId" ]; then continue; fi
        # 'if [ "$(docker ps -a | grep tendermint_'${idx}')" ]; then docker rm -f tendermint_'${idx}'; fi && '
        cmd="docker logs --timestamps $container"
        # tendermint_${idx_group}_${idx_node} -> tendermint_${idx_node}
        logname='tendermint_'$(echo $container | cut -d '_' -f 3)
        ssh -n $remote_ip "$cmd" >$log/$container.log 2>&1 &
    fi
done < $containers
wait