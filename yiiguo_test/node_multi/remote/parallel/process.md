```sh
# 初始化:
# - 生成节点配置文件和验证者信息
# - 编译镜像并 save
# - 发送镜像到 server 并 load
# 初始化和启动脚本分开, 多组的时候只需要初始化一次即可
init.sh $node_num 
# 启动 tendermint:
# 只负责启动一组节点
start.sh $groupId $port_p2p $port_rpc
```
服务器需要预留端口: 26651-26690
- port_p2p: 26651-26670 
- port_rpc: 26671-26690
即: 每台服务器最多启动 20 个 tendermint
> 注意: 防火墙要打开这些端口

```sh
# 任务分配程序: (分组数量 $D: 最大不超过 20 )
# - 生成所有实验指标, 共 $N 组
# - 通过消息队列运行 $D 组实验环境,
master.sh 
```
