# -*- coding: utf-8 -*-
"""
timestamp=1718478310543
basepath=yiiguo_scripts/output/sendtx_group_1718478310545/bi30-pn20-bc30-rt025
python yiiguo_scripts/process.py \
    --process_type=remote \
    --process_id=$timestamp \
    --process_tx_file=$basepath/$timestamp \
    --process_log_path=$basepath/remote_log/$timestamp \
    --process_output_path=$basepath/output/process
程序执行参数:
    process_type: 要处理的类型, 有 local 和 remote 两种类型, 对应着两个函数, 分数是: process_local(), process_remote(). 之后可能会把这个参数消除掉
    process_id: 处理的id
        local: 自定义
        remote: 即 yiiguo_scripts/sendtx_para_random.py 中提到的实验数据文件的时间戳文件名 {timestamp}
    process_tx_file: 交易执行结果的路径
        local: 自定义
        remote: 即 yiiguo_scripts/sendtx_para_random.py 中提到的实验数据文件
    process_log_path: 容器日志文件所在的文件夹
        local: 自定义
        remote: 即 yiiguo_scripts/sendtx_para_random.py 中提到的 remote_log/{timestamp} 文件夹
    process_output_path: 处理结果所在的文件夹, 处理结果的文件包括 {process_id}_item 和 {process_id}_mean
        local: 自定义
        remote: 即 yiiguo_scripts/sendtx_para_random.py 中提到的数据文件夹下的 output/{process_id} 文件夹
"""
import enum
import traceback
from nis import match
import os, sys
import re
import functools
import json
import numpy as np
import argparse
import time

"""
2022-04-25T16:38:34+08:00 INFO yiiguo inserted to mempool height=4 module=mempool num_txs=1 priority=0 timestamp=1650875914874361905 tx=F0E4BFA20994057CA9FC73D2F1771248CBBAD347B3C5792D3050102A333628FD version=v1
2022-04-25T16:37:44+08:00 INFO yiiguo pick txs from mempool height=1 module=consensus timestamp=1650875864144992168
2022-04-25T16:37:44+08:00 INFO yiiguo timestamp enterpropose=1650875864144054588 height=1 module=consensus round=0
2022-04-25T16:37:44+08:00 INFO yiiguo timestamp enterPrevote=1650875864149274709 height=1 module=consensus round=0
2022-04-25T16:37:44+08:00 INFO yiiguo timestamp enterPrecommit=1650875864151545543 height=1 module=consensus round=0
2022-04-25T16:37:44+08:00 INFO yiiguo timestamp commit_round=0 enterCommit=1650875864153717267 height=1 module=consensus
"""

def order(x, y):
    h0,t0 = int(x[0]), int(x[1])
    h1,t1 = int(y[0]), int(y[1])
    if h0 == h1:
        if t0 < t1:
            return -1
        elif t0 == t1:
            return 0
        else:
            return 1
    elif h0 < h1:
        return -1
    else:
        return 1

def filter(records):
    records = sorted(records, key=functools.cmp_to_key(order))
    new_records = []
    for idx in range(len(records)-1):
        if records[idx][0] != records[idx+1][0]:
            new_records.append(records[idx])
    if len(records) > 0:
        new_records.append(records[-1])
    return new_records

def get_txs(process_tx_file):
    infos = []
    with open(process_tx_file, 'r') as f:
        for info in f.readlines()[1:]:
            if len(info) > 0:
                info = json.loads(info)
                # if info['idx'] >= 0: continue # 为什么只算了区块头???
                infos.append(info)
    tx_size = len(infos)
    # print(f"tx_size: {len(infos)}")
    startpoint = int(len(infos)//20)
    endpoint = len(infos)-int(len(infos)//20)
    infos = infos[startpoint:endpoint]
    tx_blocks = {
        info['txhash']: {
            'height': info['block'], 
            'timestamp': info['start'],
            'blockts': time.mktime(time.strptime(info['block_time'].split('.')[0],"%Y-%m-%dT%H:%M:%S")) + float('0.'+info['block_time'].split('.')[1][:-1]),
            'proposer': info['proposer'],
            'incs': info['incs'],
            'unconfirmd': info['unconfirmd']
        } for info in infos 
    }
    return tx_blocks, tx_size

def filter_insert(records):
    return filter(records)
        
def filter_pick(records):
    return filter(records)

def filter_enterpropose(records):
    for idx in range(len(records)):
        records[idx][0], records[idx][1] = records[idx][1], records[idx][0]
    return filter(records)

def filter_enterPrevote(records):
    for idx in range(len(records)):
        records[idx][0], records[idx][1] = records[idx][1], records[idx][0]
    return filter(records)

def filter_enterPrecommit(records):
    for idx in range(len(records)):
        records[idx][0], records[idx][1] = records[idx][1], records[idx][0]
    return filter(records)

def filter_enterCommit(records):
    for idx in range(len(records)):
        records[idx][0], records[idx][1] = records[idx][1], records[idx][0]
    return filter(records)

def filter_endCommit(records):
    for idx in range(len(records)):
        records[idx][0], records[idx][1] = records[idx][1], records[idx][0]
    return filter(records)

ops = {
        'insert': (
            'INFO yiiguo inserted to mempool height=(\d+).*timestamp=(\d+) tx=([0-9A-Za-z]+)',
            filter_insert
        ),
        'pick': (
            'INFO yiiguo pick txs from mempool height=(\d+).*timestamp=(\d+)',
            filter_pick
        ),
        'enterpropose': (
            'INFO yiiguo timestamp enterpropose=(\d+).*height=(\d+)',
            filter_enterpropose
        ),
        'enterPrevote': (
            'INFO yiiguo timestamp enterPrevote=(\d+).*height=(\d+)',
            filter_enterPrevote
        ),
        'enterPrecommit': (
            'INFO yiiguo timestamp enterPrecommit=(\d+).*height=(\d+)',
            filter_enterPrecommit
        ),
        'enterCommit': (
            'INFO yiiguo timestamp.*enterCommit=(\d+).*height=(\d+)',
            filter_enterCommit
        ),
        'endCommit': (
            'INFO yiiguo timestamp.*endCommit=(\d+).*height=(\d+)',
            filter_endCommit
        ),
    }

def insert_map(logfiles: list):
    """
    {
        {txhash}: {
            {log.id}: {timestamp},
        }
    }
    """
    result = {}
    compiler = re.compile('timestamp=(\d+).*tx=([0-9a-zA-Z]+)')
    for idx, logfile in enumerate(logfiles):
        cmd = ('cat {} | grep "INFO yiiguo inserted to mempool"').format(logfile)
        f = os.popen(cmd)
        inserts = f.readlines()
        for insert in inserts:
            matches = compiler.findall(insert)
            if len(matches) > 0:
                match = matches[0]
                ts, txhash = match[0], match[1]
                if result.get(txhash, None) is None:
                    result[txhash] = {}
                result[txhash][idx] = int(ts)
    return result                

def height_map(logfiles: list):
    rcrd_height = {}
    for idx, logfile in enumerate(logfiles):
        result = {k: [] for k, _ in ops.items()}
        f = os.popen('cat {} | grep "INFO yiiguo "'.format(logfile))
        info = f.read()
        records = info.splitlines()
        for record in records:
            for key, op in ops.items():
                matches = re.findall(op[0], record)
                if len(matches) > 0:
                    result[key].append(list(matches[0]))

        clean_records = {}
        for key, value in result.items():
            clean_record = ops[key][1](value)
            clean_records[key] = clean_record
        
        """
        {
            "{height:str}": {
                "pick": {
                    {logidx}: timestamp:int
                },
                "enter*": {
                    {logidx}: timestamp:int
                }
            }
        }
        """
        for key, rcrds in clean_records.items():
            if key == 'insert':
                continue
            for record in rcrds:
                height = record[0]
                if rcrd_height.get(height, None) is None:
                    rcrd_height[height] = {}
                if rcrd_height[height].get(key, None) is None:
                    rcrd_height[height][key] = {}
                rcrd_height[height][key][idx] = int(record[1])
    return rcrd_height

def process1(logfile: str):
    
    result = {k: [] for k, _ in ops.items()}
    
    f = os.popen('cat {} | grep "INFO yiiguo "'.format(logfile))
    info = f.read()
    records = info.splitlines()
    for record in records:
        for key, op in ops.items():
            matches = re.findall(op[0], record)
            if len(matches) > 0:
                result[key].append(list(matches[0]))

    clean_records = {}
    for key, value in result.items():
        clean_record = ops[key][1](value)
        clean_records[key] = clean_record
    
    """
    {
        "{height:str}": {
            "pick": {timestamp:int},
            "enter*": {timestamp:int}
        }
    }
    """
    rcrd_height = {}
    for key, rcrds in clean_records.items():
        if key == 'insert':
            continue
        for record in rcrds:
            height = record[0]
            if rcrd_height.get(height, None) is None:
                rcrd_height[height] = {}
            rcrd_height[height][key] = int(record[1])
    
    """
    {
        "{txhash}": {
            "broadcast": {ts_insert} - {ts_start}
            "mempool": {ts_pick} - {ts_insert},
            "cs0": {ts_prevote} - {ts_propose},
            "cs1": {ts_precommit} - {ts_prevote},
            "cs2": {ts_propose_next_height} - {ts_commit}
        }
    }
    """
    tx_cost = {}
    for record_tx in clean_records['insert']:
        height, timestamp, txhash, start_ts = record_tx
        record = rcrd_height[height]
        tx_cost[txhash] = {
            'broadcast': int(timestamp)-start_ts,
            'mempool': record['pick']-int(timestamp),
            'cs0': record['enterPrevote']-record['enterpropose'],
            'cs1': record['enterPrecommit']-record['enterPrevote'],
            'cs2': record['enterCommit']-record['enterPrecommit'],
            'cs3': rcrd_height[str(int(height)+1)]['enterCommit']-record['enterPrecommit'],
        }
    
    keys = tx_cost[list(tx_cost.keys())[0]].keys()
    tx_cost_mean = {
        key: np.mean([info[key] for k, info in tx_cost.items()]) for key in keys 
    }

    return tx_cost_mean, tx_cost

def process2(txinfo: dict, logfile: str):
    f = os.popen('cat {} | grep -E " height={}[^0-9]"'.format(logfile, txinfo['height']))
    info = f.read()
    records = info.splitlines()
    # print(records)

    result = {}
    for record in records:
        for key, op in ops.items():
            match = op(record, txinfo)
            if len(match) > 0:
                if result.get(key, None) is None:
                    result[key] = match # 直接获取到时间戳
    # print(result)

    cmd = ('cat {} | '
    'grep "INFO yiiguo inserted to mempool" | '
    'grep tx={} | '
    'grep -Eo "timestamp=([0-9]+)" | '
    'grep -Eo "[0-9]+"').format(logfile, txinfo['txhash'])
    f = os.popen(cmd)
    insert_ts = int(f.read().strip(' \n\r'))

    cmd = ('cat {} | '
    'grep "INFO yiiguo timestamp enterpropose" | '
    'grep -E " height={}[^0-9]" | '
    'grep -Eo "enterpropose=([0-9]+)" | '
    'grep -Eo "[0-9]+"').format(logfile, int(txinfo['height'])+1)
    f = os.popen(cmd)
    propose_next = int(f.read().strip(' \n\r'))
    
    start_ts = txinfo['timestamp']
    tx_data = {
        'broadcast': insert_ts-start_ts,
        'mempool': result['pick']['timestamp']-insert_ts,
        'cs0': result['enterPrevote']['timestamp']-result['enterpropose']['timestamp'],
        'cs1': result['enterPrecommit']['timestamp']-result['enterPrevote']['timestamp'],
        'cs2': result['enterCommit']['timestamp']-result['enterPrecommit']['timestamp'],
        'cs3': propose_next-result['enterCommit']['timestamp'],

    }
    return tx_data

def process(logfiles, tx_infos, validator_map):
    rcrd_height = height_map(logfiles)
    rcrd_insert = insert_map(logfiles)
        
    tx_data = {}
    block_info = {}
    block_ts = {}
    for txhash, info in tx_infos.items():
        if info['incs'] == -1: continue
        try:
            logidx = validator_map[info['proposer']]
            insert_ts = rcrd_insert[txhash][logidx]
            height = str(info['height'])
            if block_info.get(height, None) is None:
                block_info[height] = 0
            block_info[height] += 1
            block_ts[height] = float(info['blockts'])
            record = rcrd_height[height]
            # latency_overall = block_ts[height] + (8*60*60) - info['timestamp']
            next_enterpropose = rcrd_height[str(int(height)+1)]['enterpropose']
            if next_enterpropose.get(logidx, None) is None:
                continue
            # next_enterpropose = next_enterpropose[list(next_enterpropose.keys())[0]]
            tx_data[txhash] = {
                'broadcast': float("{:.2f}".format(insert_ts-int(info['timestamp']))),
                'mempool': float("{:.2f}".format(record['enterpropose'][logidx]-int(insert_ts))),
                'cs0': float("{:.2f}".format(record['enterPrevote'][logidx]-record['enterpropose'][logidx])),
                'cs1': float("{:.2f}".format(record['enterPrecommit'][logidx]-record['enterPrevote'][logidx])),
                'cs2': float("{:.2f}".format(record['enterCommit'][logidx]-record['enterPrecommit'][logidx])),
                # 'cs3': float("{:.2f}".format(rcrd_height[str(int(height)+1)]['enterCommit'][logidx]-record['enterPrecommit'][logidx])), # 这里有问题
                # 'cs3': float("{:.2f}".format(record['endCommit'][logidx]-record['enterCommit'][logidx])),
                'cs3': float("{:.2f}".format(next_enterpropose[logidx]-record['enterCommit'][logidx])),
                'incs': float("{:.2f}".format(info['incs'])),
                'uncfmd_all': float("{:.2f}".format(info['unconfirmd'])),
                'uncfmd': float("{:.2f}".format(info['unconfirmd']-info['incs'])),
                'latency_overall': float("{:.2f}".format((next_enterpropose[logidx]-info['timestamp'])/(10**9)))
            }
        except Exception as e:
            print("error, ignore txhash: {}, info: {}, err: {}".format(txhash, info, traceback.format_exc()))
    print("stuck!!!")
    if len(tx_data) == 0:
        return {}, {}
    block_real_size = float("{:.2f}".format(sum(block_info.values())/len(block_info)))
    heights = [int(x) for x in list(block_info.keys())]
    height_min, height_max = min(heights), max(heights)
    latency_in_tps = float("{:.2f}".format(block_ts[str(height_max)]-block_ts[str(height_min)]))
    tps = float("{:.2f}".format(sum(block_info.values())/latency_in_tps))
    o_max, o_min = block_ts[str(height_max)]+(8*60*60), min(float(v['timestamp']) for v in list(tx_infos.values()))/(10**9)
    # latency_overall = float("{:.2f}".format(o_max - o_min))
    # for txhash, info in tx_infos.items():
    #     if txhash not in tx_data: continue
    #     height = str(info['height'])
    #     ts = block_ts.get(str(int(height)+1), 0)
    #     startts = info['timestamp']/(10**9)
    #     latency = 0
    #     if ts == 0:
    #         latency = 3
    #     else:
    #         latency = ts + (8*60*60) - startts
    #     tx_data[txhash]['latency_overall'] = float("{:.2f}".format(latency))
    #     tx_data[txhash]['startts'] = startts
    #     tx_data[txhash]['endts'] = ts
            

    
    keys = tx_data[list(tx_data.keys())[0]].keys()
    tx_data_mean = {
        key: float("{:.2f}".format(np.mean([info[key] for _, info in tx_data.items()]) ))
        for key in keys 
    }
    tx_data_mean['tx_size'] = len(tx_data)
    tx_data_mean['block_real_size'] = block_real_size
    tx_data_mean['sum(block_info.values())'] = sum(block_info.values())
    tx_data_mean['len(block_info)'] = len(block_info)
    # tx_data_mean['tps'] = float(f"{tps:.2f}")
    tx_data_mean['tps'] = tps
    tx_data_mean['latency_in_tps'] = latency_in_tps
    tx_data_mean['avg_latency_in_tps'] = float("{:.2f}".format(latency_in_tps/len(heights)))
    # tx_data_mean['latency_overall'] = latency_overall # (blocktime+1) - starttime
    tx_data_mean['o_max'] = o_max
    tx_data_mean['o_min'] = o_min

    # tx_data_mean['heights'] = sorted(int(x) for x in block_info.keys())
    return tx_data_mean, tx_data


def process_local(process_txs_path, log_path):
    genesis = json.load(open('./yiiguo_test/node_single/node/config/genesis.json', 'r'))
    validators = genesis['validators']
    validator_map = {validator['address']:idx for idx, validator in enumerate(validators)}

    logfiles = ['./yiiguo_test/node_single/tendermint.log']
    
    tx_infos, tx_size = get_txs(process_txs_path)
    tx_cost_mean, tx_cost = process(logfiles, tx_infos ,validator_map)
    return tx_cost_mean, tx_cost

def process_remote(process_tx_file, remotelog_path):
    genesis = json.load(open('./temp/node0/config/genesis.json', 'r'))
    validators = genesis['validators']
    validator_map = {validator['address']:idx for idx, validator in enumerate(validators)}

    # logfile_prefix = './yiiguo_test/node_multi_remote/log'
    logfiles = [os.path.join(remotelog_path, 'tendermint_{}.log'.format(idx)) for idx in range(len(validators))]
    for logfile in logfiles:
        if not os.path.exists(logfile):
            raise Exception("log file not exists! logfile: {}".format(logfile))

    tx_infos, tx_size = get_txs(process_tx_file)
    if len(tx_infos) == 0:
        return {}, {}
    tx_cost_mean, tx_cost = process(logfiles, tx_infos ,validator_map)
    tx_cost_mean['tx_size'] = tx_size
    return tx_cost_mean, tx_cost
    
def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process_type", type=str)
    parser.add_argument("--process_id", type=str)
    parser.add_argument("--process_tx_file", type=str)
    parser.add_argument("--process_log_path", type=str)
    parser.add_argument("--process_output_path", type=str)

    return parser.parse_args()

if __name__ == '__main__':
    args = getArgs()
    process_type = args.process_type
    process_id = args.process_id
    process_tx_file = args.process_tx_file
    process_log_path = args.process_log_path
    process_output_path = os.path.join(args.process_output_path, process_id)
    if not os.path.exists(process_output_path):
        os.makedirs(process_output_path)

    if process_type == 'local':
        tx_cost_mean, tx_cost = process_local(process_tx_file, process_log_path)
    elif process_type == 'remote':
        tx_cost_mean, tx_cost = process_remote(process_tx_file, process_log_path)
    else:
        raise Exception("invalid type")
    
    output_item = os.path.join(process_output_path, "item")
    output_mean = os.path.join(process_output_path, "mean")
    json.dump(tx_cost, open(output_item, 'w'), indent=4)
    json.dump(tx_cost_mean, open(output_mean, 'w'), indent=4)