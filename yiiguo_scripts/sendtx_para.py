# curl -s 'localhost:26657/broadcast_tx_commit?tx="abcd"
from genericpath import exists
import requests
import threading
import time
import sys
import os
import json
import random
import loguru

PARA_NUM = [2,5,10,20,50,75,100,150,200]
# PARA_NUM = [2,5]
BLOCK_INTERVAL = [5,10,15,30,60,120,300,600]
BLOCK_CAP = [10,15,20,25,30,35,40,45,50]
RATIO = [0.001,0.01,0.05,0.1,0.25,0.5,0.75,1]
# RATIO = [0.001,0.01]
RATIO_POINT = 1000
BLOCKALL = 10000

dir_path = os.path.dirname(__file__)
output_dir = os.path.join(dir_path, "sendtx_para_output")
log_dir = os.path.join(output_dir, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logger = loguru.logger
logger.remove()
logger.add(
    os.path.join(log_dir, "{}.log".format(__file__)),
    mode='w',
    # format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    # "<level>{level: <8}</level> | "
    # "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

def send_tx(metrics: dict, para_idx: int, tx_idx: int, header: bool):
    logger.info("send tx: para-{}, txidx-{}, header-{}".format(para_idx, tx_idx, header))

    # query unconfirmed tx number in mempool
    url_uncfmtxs = 'http://10.21.4.36:26657/num_unconfirmed_txs'
    result = requests.get(url_uncfmtxs)
    result.raise_for_status()
    uncfmtxs = json.loads(result.text)
    num_uncfm = uncfmtxs.get('result', {}).get('n_txs', None)
    if num_uncfm is None:
        msg = "query unconfirmed tx num failed! status_code: {}".format(result.status_code)
        logger.error(msg)
        return
    num_uncfm = int(num_uncfm)
    
    # send tx and measure the cost time
    start_time = time.time()
    url = 'http://10.21.4.36:26657/broadcast_tx_sync?tx="selftxinfo={},{},{}"'.format(time.time(),para_idx,tx_idx)
    result = requests.get(url)
    result.raise_for_status()
    if not isinstance(metrics.get(para_idx), dict):
        metrics[para_idx] = {}
    metrics[para_idx][tx_idx] = {
        'start': start_time,
        'cost': time.time() - start_time,
        'unconfirmd': num_uncfm,
        'header': header,
    }

def para_chain(metrics, output_dir_each_exp: str, para_idx: int, block_num: int, block_interval: int, block_cap: int, ratio: float):
    logger.info("{:*^50}".format("deal parachain-{}, blockall-{}".format(para_idx, block_num)))
    start_time = time.time()
    ratio_pcnt = int(ratio*RATIO_POINT)
    tx_idx_round = 0
    tx_idx = 0
    block_idx = 1
    threads = []
    cross_indexes = random.sample(range(RATIO_POINT), ratio_pcnt)
    logger.info("new random sequence: {}".format(cross_indexes))
    while True:
        logger.info("new block: para-{}, block-{}".format(para_idx, block_idx))
        # send header tx
        thread_header = threading.Thread(
            target=send_tx,
            args=(metrics, para_idx, -1, True)
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
            if tx_idx_round in cross_indexes:
                logger.info("cross tx found: para-{}, block-{}, txidx-{}, txidxround-{}", para_idx, block_idx, tx_idx, tx_idx_round)
                thread_tx = threading.Thread(
                    target=send_tx, 
                    args=(metrics, para_idx, tx_idx, False)
                )
                thread_tx.start()
                threads.append(thread_tx)
        block_idx += 1
        if block_idx > block_num:
            for thread in threads:
                thread.join()
            break
        # 平行链区块生成间隔
        time.sleep(block_interval)

    output_path = os.path.join(output_dir_each_exp, "para_{}".format(para_idx))
    json.dump(metrics[para_idx], open(output_path, 'w'))
    end_time = time.time()
    logger.info("para-{} done! cost time: {}".format(para_idx, end_time-start_time))
    logger.info("write result({}) to {}".format(para_idx, output_path))

def start(block_interval: int, para_num: int, block_cap: int, ratio: float):
    logger.info("{:*^100}".format("measuring: paranum-{}, interval-{}, cap-{}, ratio-{}".format(para_num, block_interval, block_cap, ratio)))
    metrics = {}
    threads = []
    output_dir_each_exp = os.path.join(output_dir, "{}-{}-{}-{}".format(para_num,block_interval,block_cap,str(ratio).replace('.','')))
    if not os.path.exists(output_dir_each_exp):
        os.makedirs(output_dir_each_exp)
    for i in range(para_num):
        block_num = BLOCKALL//para_num + (1 if BLOCKALL%para_num > i else 0)
        threads.append(
            threading.Thread(
                target=para_chain, 
                args=(metrics, output_dir_each_exp, i, block_num, block_interval, block_cap, ratio)
            )
        )
    start_time = time.time()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    end_time = time.time()
    logger.info("all para done! cost time: {}".format(end_time-start_time))

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
        start(
            15,
            10,
            30,
            rat
        )
    
    # change para num
    for para in PARA_NUM:
        start(
            15,
            para,
            30,
            0.05
        )
    
    # # change block interval
    # for interval in BLOCK_INTERVAL:
    #     start(
    #         interval,
    #         10,
    #         30,
    #         0.25
    #     )
    pass

    