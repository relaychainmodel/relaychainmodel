# -*- coding: utf-8 -*-
"""
功能：
    每组数据实验开始前, 重新启动 tendermint 容器, 结束之后, 将容器所产生的日志保存到
    统计 BLOCKALL = 10000 个区块
    先发送区块头交易
    每 0.1 秒检查是否满足条件（一个公式），如果满足，则发送交易
    发送交易的过程也单独开一个线程，为了使该过程能够尽可能的小于0.01秒

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
import multiprocessing
from queue import Queue
from numpy import block, true_divide
import requests
import threading
import time
import sys
import os
import json
import random
import loguru
import subprocess

MAX_RETRY_TIMES = 5
MAX_RETRY_DUR = 3
MAX_SLEEP_DUR = 60
MAX_SLEEP_TIMES = 5

class Sender:
    def __init__(self, 
        url: str,
        expargs: dict,
        ratio_point: int=1000,
        blockall: int=10000,
        check_delta: float=0.01,
        expid: str=str(int(time.time()*1000)),
        outputdir: str=None,
        logdir: str=None
    ) -> None:
        """
            block_interval,
            para_num,
            block_cap,
            str(ratio).replace('.','')
        """
        self.arg_block_interval = expargs['block_interval']
        self.arg_para_num = expargs['para_num']
        self.arg_block_cap = expargs['block_cap']
        self.arg_ratio = expargs['ratio']
        self.chain_url = url
        self.ratio_point = ratio_point
        self.blockall = blockall
        self.check_delta = check_delta
        self.timestamp = expid
        self.output_dir = outputdir
        self.log_dir = logdir
        self.logger_name = "{}_{}".format(self.get_expkey(),"sender")
        self.logger = loguru.logger.bind(expkey=self.logger_name)
        self.cross_indexes = {
            x: True 
            for x in random.sample(
                range(self.blockall*self.arg_block_cap), 
                int(self.blockall*self.arg_block_cap*self.arg_ratio)
            )
        }
        if not self.output_dir:
            dir_path = os.path.dirname(__file__)
            self.output_dir = os.path.join(dir_path, "output", "sendtx_para_random_output_{}".format(self.timestamp))
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except FileExistsError as e:
                pass
        if not self.log_dir:
            self.log_dir = os.path.join(outputdir, "logs")
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except FileExistsError as e:
                pass
        
    def get_expkey(self):
        return "bi{}-pn{}-bc{}-rt{}".format(
            self.arg_block_interval,
            self.arg_para_num,
            self.arg_block_cap,
            str(self.arg_ratio).replace('.','')
        )

    def retry_requests(self, request_method, request_args: dict, func_name: str):
        # url=url, headers={'Connection':'close'}
        cnt_err = 0
        cnt_sleep = 0
        starttime = time.time()
        while cnt_err < MAX_RETRY_TIMES:
            try:
                result = request_method(**request_args)
                break
            except Exception as e:
                self.logger.error("{} exception: {}, retry {} after {}s, url: {}".format(func_name, e, cnt_err, MAX_RETRY_DUR, request_args['url']))
                time.sleep(MAX_RETRY_DUR)
            cnt_err += 1
            if cnt_err == MAX_RETRY_TIMES:
                self.logger.error("{} retry too many({} times), ready to sleep..., url: {}".format(func_name, cnt_err, request_args['url']))
                time.sleep(MAX_SLEEP_DUR)
                cnt_err = 0
                cnt_sleep += 1
            if cnt_sleep == MAX_SLEEP_TIMES:
                error = "{} sleep too long({})! url: {}".format(func_name, time.time()-starttime, request_args['url'])
                self.logger.error(error)
                raise Exception(error)
        return result

    def query_by_rpc(self):
        url='http://{}/num_unconfirmed_txs'.format(self.chain_url)
        request_args = {
            'url': url,
            'headers': {'Connection':'close'}
        }
        result = self.retry_requests(request_method=requests.get, request_args=request_args, func_name='query by rpc')
        try:
            info = json.loads(result.text)
            incs = int(info['result']['n_txs'])
            uncfm = int(info['result']['total'])
            return incs, uncfm, ""
        except Exception as e:
            return 0, 0, "query_by_rpc exception, err: {}".format(e)



    def send_tx(self, metrics: dict, idx: int, que_tx: Queue):
        
        # 获取共识中的交易数量 和 未确认的交易数
        txnum_in_cs = 0
        txnum_in_cs, txnum_uncfm, err = self.query_by_rpc()
        if txnum_in_cs == -1:
            self.logger.warning("query_by_rpc failed, error: txnum_in_cs=-1, no tx_incs file")
        if err != "":
            txnum_in_cs = -1
            txnum_uncfm = -1
            self.logger.error("query_by_rpc exception, error: {}".format(err))        

        # 发送交易
        start_time = time.time_ns()    
        url = 'http://{}/broadcast_tx_async?tx="{}-{}"'.format(self.chain_url, int(time.time()*1000), idx)    
        request_args = {
            'url': url,
            'headers': {'Connection':'close'}
        }
        result = self.retry_requests(request_method=requests.get, request_args=request_args, func_name='send tx')
        try:
            txhash = json.loads(result.text)['result']['hash']
        except Exception as e:
            self.logger.error("send tx failed! exception: {}. result: {}".format(e, result.text))
            return
        self.logger.info("{} {} {} {} {}".format(idx, result.status_code, txnum_in_cs, txnum_uncfm, txhash))
        
        # 放入交易队列, 在 waiter 中取出
        item = {
            'idx': idx,
            'start': start_time,
            'cost_send': time.time_ns() - start_time,
            'cost_wait': 0,
            'block': 0,
            'txhash': txhash,
            'proposer': "",
            'unconfirmd': txnum_uncfm,
            'incs': txnum_in_cs,
        }
        que_tx.put(item)

    def check_xtx(self) -> bool:
        return random.randint(1,100) <= self.arg_ratio*100

    def send_block(self, block_idx: int, metrics: dict, que_tx: Queue):
        threads = []
        thread_header = threading.Thread(
            target=self.send_tx,
            args=(metrics, -block_idx, que_tx)
        )
        thread_header.start()
        threads.append(thread_header)

        # random cross tx, and
        # send cross tx
        tx_idx = (block_idx-1)*self.arg_block_cap
        self.logger.info("tx_idx check: {}".format(tx_idx))
        for _ in range(self.arg_block_cap):
            # if self.cross_indexes.get(tx_idx, False):
            if self.check_xtx():
                self.logger.info("cross tx found: block({}), txidx({})".format(block_idx, tx_idx))
                thread_tx = threading.Thread(
                    target=self.send_tx, 
                    args=(metrics, tx_idx, que_tx)
                )
                thread_tx.start()
                threads.append(thread_tx)
            tx_idx += 1
        for thread in threads:
            thread.join()     

    def start(self, que_tx: Queue):
        loggerid =self.logger.add(
            os.path.join(self.log_dir, "{}.log".format(self.logger_name)),
            mode='w',
            filter=lambda record: record['extra']['expkey'] == self.logger_name
        )
        self.logger.info("{:*^100}".format(
            "measuring: paranum({}), interval({}), cap({}), ratio({})".format(
                self.arg_para_num, 
                self.arg_block_interval, 
                self.arg_block_cap, 
                self.arg_ratio)
            )
        )

        start_time = time.time()
        metrics = {}
        threads = []
        block_idx = 1
        block_starttime = 0
        block_endtime = 0
        while True:
            x = random.randint(0, 10000)
            block_starttime = time.time()
            if x <= self.check_delta*10000/(self.arg_block_interval/(self.arg_para_num+0.0)): # UnLOG: 每秒有 arg_para_num/block_interval 个区块产生，那么 check_delta 秒内有多少个区块产生
                inner_starttime = time.time()
                # begin: send block
                threads.append(
                    threading.Thread(
                        target=self.send_block,
                        args=(block_idx, metrics, que_tx)
                    )
                )
                threads[-1].start()
                # end: send block
                inner_endtime = time.time()
                self.logger.info("send block cost: {}, blockidx: {}".format(int((inner_endtime-inner_starttime)*1000), block_idx))
                block_idx += 1
                if block_idx > self.blockall:
                    for thread in threads:
                        thread.join()
                    break

            block_endtime = time.time()
            resttime = self.check_delta - (block_endtime-block_starttime)
            self.logger.info(f"resttime: {resttime}, block_index: {block_idx}")
            if resttime > 0:
                time.sleep(resttime)
            pass

        end_time = time.time()

        que_tx.put({'stop': True})
        self.logger.info("done! cost time: {}".format(end_time-start_time))
        self.logger.remove(loggerid)


class Waiter(object):

    def __init__(self, 
        url: str,
        outputdir: str=None,
        logdir: str=None,
        expkey: str=None,
        expid: str=str(int(time.time()*1000))
    ) -> None:
        """
            block_interval,
            para_num,
            block_cap,
            str(ratio).replace('.','')
        """
        self.chain_url = url
        self.timestamp = expid
        self.expkey = expkey
        self.output_dir = outputdir
        self.log_dir = logdir
        self.logger_name = "{}_{}".format(self.expkey,"waiter")
        self.logger = loguru.logger.bind(expkey=self.logger_name)

        if not self.output_dir:
            dir_path = os.path.dirname(__file__)
            self.output_dir = os.path.join(dir_path, "output", "sendtx_para_random_output_{}".format(self.timestamp))
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except FileExistsError as e:
                pass
        
        output_dir_each_exp = os.path.join(self.output_dir, self.expkey)
        if not os.path.exists(output_dir_each_exp):
            os.makedirs(output_dir_each_exp)
        output_name = self.timestamp
        self.output_file = os.path.join(output_dir_each_exp, "{}".format(output_name))
        
        if not self.log_dir:
            self.log_dir = os.path.join(outputdir, "logs")
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except FileExistsError as e:
                pass

    def retry_requests(self, request_method, request_args: dict, func_name: str):
        # url=url, headers={'Connection':'close'}
        cnt_err = 0
        cnt_sleep = 0
        starttime = time.time()
        while cnt_err < MAX_RETRY_TIMES:
            try:
                result = request_method(**request_args)
                break
            except Exception as e:
                self.logger.error("{} exception: {}, retry {} after {}s, url: {}".format(func_name, e, cnt_err, MAX_RETRY_DUR, request_args['url']))
                time.sleep(MAX_RETRY_DUR)
            cnt_err += 1
            if cnt_err == MAX_RETRY_TIMES:
                self.logger.error("{} retry too many({} times), ready to sleep..., url: {}".format(func_name, cnt_err, request_args['url']))
                time.sleep(MAX_SLEEP_DUR)
                cnt_err = 0
                cnt_sleep += 1
            if cnt_sleep == MAX_SLEEP_TIMES:
                error = "{} sleep too long({})! url: {}".format(func_name, time.time()-starttime, request_args['url'])
                self.logger.error(error)
                raise Exception(error)
        return result

    def waitTx(self, txhash):
        time_delta = 0.5
        time_count = 200
        while time_count > 0:
            url = 'http://{}/tx?hash=0x{}'.format(self.chain_url, txhash)  
            for _ in range(MAX_RETRY_TIMES*10): # wait tx 多等待一会儿
                try:
                    result = requests.get(url, headers={'Connection':'close'})
                    break
                except:
                    time.sleep(MAX_RETRY_DUR)
            if result is None:
                continue
            info = json.loads(result.text)
            result = info.get('result', None)
            if result is not None:
                return int(info['result']['height']), ""        
            time.sleep(time_delta)
            time_count -= 1
        return -1, "timeout!not found!"

    def getProposer(self, height: int):
        
        url = 'http://{}/block?height={}'.format(self.chain_url, height)    
        request_args = {
            'url': url,
            'headers': {'Connection':'close'}
        }
        result = self.retry_requests(request_method=requests.get, request_args=request_args, func_name='get proposer')
        try:
            info = json.loads(result.text)
        except Exception as e:
            return "", "", "getProposer exception: {}, height: {}".format(e, height)
            
        result = info.get('result', None)
        if result is not None:
            return info['result']['block']['header']['proposer_address'], info['result']['block']['header']['time'], ""
        else:
            return "", "", "getProposer exception: {}, height: {}".format(info, height)
    
    def start(self, quetx: Queue): 
        loggerid =self.logger.add(
            os.path.join(self.log_dir, "{}.log".format(self.logger_name)),
            mode='w',
            filter=lambda record: record['extra']['expkey'] == self.logger_name
        )
        metrics = {}

        while True:
            txinfo:dict = quetx.get(block=True)
            if txinfo.get('stop', False):
                break
            txhash = txinfo['txhash']
            txidx = txinfo['idx']
            block = -1
            proposer_address = ""
            block_time = ""
            self.logger.info("wait for tx({}:{})".format(txidx, txhash))
            block, error = self.waitTx(txhash)
            if error != "":
                self.logger.error("wait tx failed! txhash: {}, error: {}".format(txhash, error))
            else:
                self.logger.info("idx: {}, block: {}, txhash: {}".format(txidx, block, txhash))
                proposer_address, block_time, error = self.getProposer(int(block))
                if error != "":
                    self.logger.error("get proposer error:{}, txhash: {}".format(error, txhash))

            txinfo.update(
                {
                    'cost_wait': time.time_ns() - txinfo['start'],
                    'block': block,
                    'block_time': block_time,
                    'proposer': proposer_address,
                }
            )
            metrics[txidx] = txinfo
            self.logger.info(txinfo)
            quetx.task_done()
        
        with open(self.output_file, 'w') as f:
            infos = ["{}\n".format(json.dumps(v)) for k,v in metrics.items()]
            f.writelines(infos)

        # json.dump(metrics, open(output_path, 'w'))
        self.logger.info("write result to {}".format(self.output_file))
        self.logger.remove(loggerid)
        

if __name__=="__main__":
    pass

    