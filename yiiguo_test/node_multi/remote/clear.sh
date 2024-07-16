#!/bin/bash
# clear containers on all servers 
# 
# desc:
# sh yiiguo_test/node_multi/remote/clear.sh groupId 
# 
# demo:
# sh yiiguo_test/node_multi/remote/clear.sh 5

set -e

base_dir=$(pwd)
containers=$base_dir/yiiguo_test/node_multi/remote/containers
groupId=$1
if [ -z "$groupId" ]; then
    echo "ERROR: need groupId"
    exit 0
fi

while read info; do
    if [ -n "$info" ]; then
        remote_ip=$(echo $info | cut -d ' ' -f 1)
        container=$(echo $info | cut -d ' ' -f 2)
        group_id=$(echo $info | cut -d ' ' -f 3)
        if [ "$groupId" != "all" ]; then
            if [ "$group_id" != "$groupId" ]; then continue; fi
        fi
        # 'if [ "$(docker ps -a | grep tendermint_'${idx}')" ]; then docker rm -f tendermint_'${idx}'; fi && '
        cmd='if [ "$(docker ps -a | grep '$container')" ]; then docker rm -f '$container'; fi'
        ssh -n $remote_ip "$cmd" &
    fi
done < $containers
wait
rm $containers