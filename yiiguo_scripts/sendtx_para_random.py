# -*- coding: utf-8 -*-
"""
功能：
    每组数据实验开始前, 重新启动 tendermint 容器, 结束之后, 将容器所产生的日志保存到
    统计 BLOCKALL = 10000 个区块
    先发送区块头交易
    每 0.1 秒检查是否满足条件（一个公式），如果满足，则发送交易

输出：
    根文件夹: yiiguo_scripts/output/sendtx_para_random_output_{timestamp}
    数据文件夹: 在根文件夹下, 每个数据文件夹以本组实验的指标命名, 包括本组实验的实验数据文件以及日志文件
    
    实验数据文件: 以时间戳 {timestamp} 命名,  每一行是json格式, 具体字段:
    {
        "idx": int, 
        "start": int(timestamp nanosecond), 
        "cost": int, 
        "block": int, 
        "txhash": str, 
        "proposer": str, 
        "unconfirmd": int, 
        "incs": int
    }
    日志文件: 在数据文件夹的 remote_log/{timestamp} 文件夹下, 时间戳和本组实验数据文件的文件名一致, 日志文件包含来自每个节点的容器日志, 通过 docker logs tendermint_0 2>&1 >tendermint_0.log 获得

实验数据处理:
    处理脚本 yiiguo_scripts/process.py 
"""
# curl -s 'localhost:26657/broadcast_tx_commit?tx="abcd"
import requests
import threading
import time
import sys
import os
import json
import random
import loguru
import subprocess

PARA_NUM = [2,5,10,20,50,75,100,150,200]
# PARA_NUM = [2,5]
BLOCK_INTERVAL = [5,10,15,30,60,120,300,600]
BLOCK_CAP = [10,15,20,25,30,35,40,45,50]
RATIO = [0.001,0.01,0.05,0.1,0.25,0.5,0.75,1]
# RATIO = [1]
RATIO_POINT = 1000
BLOCKALL = 10000
CHECK_DELTA = 0.01
CHAIN_HOST="10.21.4.37"
CHAIN_PORT="26657"
CHAIN_URL="{}:{}".format(CHAIN_HOST, CHAIN_PORT)

dir_path = os.path.dirname(__file__)
output_dir = os.path.join(dir_path, "output", "sendtx_para_random_output_{}".format(int(time.time()*1000)))
log_dir = os.path.join(output_dir, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logger = loguru.logger
logger.remove()
logger.add(
    os.path.join(log_dir, "{}.log".format(os.path.basename(__file__))),
    mode='w',
    # format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    # "<level>{level: <8}</level> | "
    # "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)


def query_by_rpc():
    result = requests.get(
        url='http://{}/num_unconfirmed_txs'.format(CHAIN_URL),
        headers={'Connection':'close'}
    )
    if result.status_code != 200:
        return 0, 0, "code: {}".format(result.status_code)
    try:
        info = json.loads(result.text)
        incs = int(info['result']['n_txs'])
        uncfm = int(info['result']['total'])
        return incs, uncfm, ""
    except Exception as e:
        return 0, 0, "query_by_rpc exception, err: {}".format(e)

def waitTx(idx, txhash):
    time_delta = 0.05
    time_count = 200
    while time_count > 0:
        url = 'http://{}/tx?hash=0x{}'.format(CHAIN_URL, txhash)    
        result = requests.get(url, headers={'Connection':'close'})
        try:
            info = json.loads(result.text)
        except Exception as e:
            info = {}
            logger.error("wait tx exception: {}".format(e))
        result = info.get('result', None)
        if result is not None:
            return int(info['result']['height']), ""        
        time.sleep(time_delta)
        time_count -= 1
    return -1, "not found"

def getProposer(height: int):
    
    url = 'http://{}/block?height={}'.format(CHAIN_URL, height)    
    result = requests.get(url, headers={'Connection':'close'})
    try:
        info = json.loads(result.text)
    except Exception as e:
        return "", "getProposer exception: {}, height: {}".format(e, height)
        
    result = info.get('result', None)
    if result is not None:
        return info['result']['block']['header']['proposer_address'], ""        

def send_tx(metrics: dict, idx: int):
    txnum_in_cs = 0
    txnum_in_cs, txnum_uncfm, err = query_by_rpc()
    if err != "":
        txnum_in_cs = -1
        txnum_uncfm = -1
        logger.error("query_by_rpc exception, error: {}".format(err))

    start_time = time.time_ns()    
    url = 'http://{}/broadcast_tx_async?tx="{}-{}"'.format(CHAIN_URL, int(time.time()*1000), idx)    
    result = requests.get(url, headers={'Connection':'close'})
    try:
        txhash = json.loads(result.text)['result']['hash']
    except Exception as e:
        txhash = ""
        logger.error("send Tx exception: {}, status_code: {}".format(e, result.status_code))
        return
    logger.info("{} {} {} {} {}".format(idx, result.status_code, txnum_in_cs, txnum_uncfm, txhash))
    block, _ = waitTx(idx, txhash)
    logger.info("idx: {}, block: {}, txhash: {}".format(idx, block, txhash))
    proposer_address, error = getProposer(int(block))
    if error != "":
        logger.error(error)
        return
    metrics[idx] = {
        'idx': idx,
        'start': start_time,
        'cost': time.time_ns() - start_time,
        'block': block,
        'txhash': txhash,
        'proposer': proposer_address,
        'unconfirmd': txnum_uncfm,
        'incs': txnum_in_cs,
    }

def start(expkey, block_interval: int, para_num: int, block_cap: int, ratio: float):
    loggerid =logger.add(
        os.path.join(log_dir, "{}.log".format(expkey)),
        mode='w'
    )
    logger.info("{:*^100}".format("measuring: paranum({}), interval({}), cap({}), ratio({})".format(para_num, block_interval, block_cap, ratio)))
        
    output_dir_each_exp = os.path.join(output_dir, expkey)
    if not os.path.exists(output_dir_each_exp):
        os.makedirs(output_dir_each_exp)

    start_time = time.time()
    metrics = {}
    threads = []
    ratio_pcnt = int(ratio*RATIO_POINT)
    tx_idx_round = 0
    tx_idx = 0
    block_idx = 1
    cross_indexes = random.sample(range(RATIO_POINT), ratio_pcnt)
    logger.info("new random sequence: {}".format(cross_indexes))
    block_starttime = 0
    block_endtime = 0
    while True:
        x = random.randint(0, 10000)
        if x <= CHECK_DELTA*10000/(block_interval/(para_num+0.0)):
            block_starttime = time.time()
            # send header tx
            thread_header = threading.Thread(
                target=send_tx,
                args=(metrics, -block_idx)
            )
            thread_header.start()
            threads.append(thread_header)

            # random cross tx, and
            # send cross tx
            for _ in range(block_cap):
                tx_idx += 1
                tx_idx_round += 1
                if tx_idx_round >= RATIO_POINT:
                    # re-random sequences for new round(length: RATIO_POINT)
                    cross_indexes = random.sample(range(RATIO_POINT), ratio_pcnt)
                    logger.info("new random sequence: {}".format(cross_indexes))
                tx_idx_round %= RATIO_POINT
                if tx_idx_round in cross_indexes:
                    logger.info("cross tx found: block({}), txidx({}), txidxround({})", block_idx, tx_idx, tx_idx_round)
                    thread_tx = threading.Thread(
                        target=send_tx, 
                        args=(metrics, tx_idx)
                    )
                    thread_tx.start()
                    threads.append(thread_tx)
            block_idx += 1
            if block_idx > BLOCKALL:
                for thread in threads:
                    thread.join()
                break
            block_endtime = time.time()
        resttime = CHECK_DELTA - (block_endtime-block_starttime)
        if resttime > 0:
            time.sleep(resttime)
        pass

    end_time = time.time()
    output_name = int(time.time()*1000)
    output_path = os.path.join(output_dir_each_exp, "{}".format(output_name))

    with open(output_path, 'w') as f:
        infos = ["{}\n".format(json.dumps(v)) for k,v in metrics.items()]
        f.writelines(infos)

    # json.dump(metrics, open(output_path, 'w'))
    logger.info("write result to {}".format(output_path))
    logger.info("done! cost time: {}".format(end_time-start_time))
    logger.remove(loggerid)
    return output_path

def restart_docker(expkey):
    logger.info("start docker... key:{}".format(expkey))
    popen = subprocess.Popen("sh yiiguo_test/node_multi/remote/start_nobuild.sh 4", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    popen.wait()
    if popen.returncode != 0:
        logger.error("start docker error, returncode: {}, out: {}, err: {}".format(popen.returncode, popen.stderr.read().decode(), popen.stdout.read().decode()))
        raise Exception("start docker error")
    logger.info("start docker out: {}".format(popen.stdout.read().decode()))
    logger.info("docker start ok!")

def get_log(expkey, output_path):
    logger.info("get log... key:{}".format(expkey))
    output_name = str(os.path.basename(output_path)).split('.')[0]
    log_dir = os.path.join(output_dir, expkey, "remote_log", output_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    popen = subprocess.Popen("sh yiiguo_test/node_multi/remote/get_log.sh {}".format(log_dir), 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    popen.wait()
    if popen.returncode != 0:
        logger.error("get log error, returncode: {}, out: {}, err: {}".format(popen.returncode, popen.stderr.read().decode(), popen.stdout.read().decode()))
        raise Exception("get log error")
    logger.info("get log out: {}".format(popen.stdout.read().decode()))
    logger.info("get log ok!")

if __name__=="__main__":

    # # change block interval
    # for cap in BLOCK_CAP:
    #     start(
    #         15,
    #         10,
    #         cap,
    #         0.05,
    #     )
    
    # change ratio
    for rat in RATIO:
        para_num, block_interval, block_cap, ratio = 10, 15, 30, rat
        expkey = "bi{}-pn{}-bc{}-rt{}".format(block_interval,para_num,block_cap,str(ratio).replace('.',''))
        restart_docker(expkey)
        output_path = start(
            expkey,
            block_interval,
            para_num,
            block_cap,
            ratio
        )
        get_log(expkey, output_path)
    
    # change para num
    for para in PARA_NUM:
        para_num, block_interval, block_cap, ratio = para, 15, 30, 0.05
        expkey = "bi{}-pn{}-bc{}-rt{}".format(block_interval,para_num,block_cap,str(ratio).replace('.',''))
        restart_docker(expkey)
        output_path = start(
            expkey,
            block_interval,
            para_num,
            block_cap,
            ratio
        )
        get_log(expkey, output_path)
    # # change block interval
    # for interval in BLOCK_INTERVAL:
    #     start(
    #         interval,
    #         10,
    #         30,
    #         0.25
    #     )
    pass

    