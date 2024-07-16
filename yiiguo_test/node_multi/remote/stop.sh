#!/bin/bash
set -e

base_dir=$(pwd)
containers=$base_dir/yiiguo_test/node_multi/remote/containers

while read info; do
    if [ -n "$info" ]; then
        remote_ip=$(echo $info | cut -d ' ' -f 1)
        container=$(echo $info | cut -d ' ' -f 2)
        ssh -n $remote_ip "docker stop $container" &
    fi
done < $containers
wait