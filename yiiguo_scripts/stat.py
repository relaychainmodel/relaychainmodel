from datetime import datetime
from functools import cmp_to_key
import json
from math import sqrt
import os
import re
import time
import matplotlib.pyplot as plt
import numpy as np
# finalizing commit of block hash=64DE2552FFA6AF8104418BCAAEDA2069FD4992C4BD66C2009954ECEF1A7FC861 height=49 module=consensus num_txs=12 root=D203000000000000
# 2022-05-07T16:25:31Z INFO finalizing commit of block hash=2DFF23F114764ABA6E779EE9920B5C149066C14EED1D0799049936BE8067E43C height=1 module=consensus num_txs=0 root=
basedir = "./yiiguo_scripts/output/sendtx_group_1651920701569"
dirs = os.listdir(basedir)
# recp = re.compile("finalizing commit of block.*(height=\d+).*(num_txs=\d+)")
keyswanted = [
    "bi15-pn2-bc30-rt005",
    "bi15-pn5-bc30-rt005",
    "bi15-pn10-bc30-rt005",
    "bi15-pn20-bc30-rt005",
    "bi15-pn50-bc30-rt005",
    "bi15-pn75-bc30-rt005",
    "bi15-pn100-bc30-rt005",
    "bi15-pn150-bc30-rt005",
    "bi15-pn200-bc30-rt005",
]
recp = re.compile("(\d+-\d+-\d+)T(\d+:\d+:\d+)Z INFO finalizing commit of block.*num_txs=(\d+)")
num_txs = {}
timestamps = {}

def compare(x: str,y: str) -> int:
    xx = str(x).split(":")[0]
    yy = str(y).split(":")[0]
    if len(xx) < len(yy): return -1
    if len(xx) > len(yy): return 1
    if xx < yy: return -1
    if xx > yy: return 1
    return 0

def fig_interval(timestamps: dict):
    idx = 1
    # row = int(sqrt(len(timestamps)))
    # col = row + 1
    row, col = 3,3
    costs = {}
    plt.figure(figsize=(20, 20))
    for key in keyswanted:
        value = timestamps[key]
        # if key not in keyswanted : continue
        costs[key] = [value[-1]-value[0], 25000/(value[-1]-value[0])]
        value = [value[i]-value[i-1] for i in range(1,len(value))]
        plt.subplot(row, col, idx)
        plt.ylim([0, 120])
        # plt.xticks(range(0,len(value),300))
        # plt.yticks(range(0,120,10))
        plt.scatter(range(len(value)), value, s=10)
        plt.title(key)
        idx += 1
    plt.savefig("fig_blocktime_interval.jpg", dpi=200)
    plt.close()
    json.dump(costs, open("out_blocktime_interval.json", 'w'))

def fig_block(num_txs: dict):
    # 画图
    row = int(sqrt(len(num_txs)))+1
    col = row
    idx = 1
    plt.figure(figsize=(20, 20))
    for key in keyswanted:
        value = num_txs[key]
    # for key,  in num_txs.items():
        # if key not in keyswanted : continue
        ypoints = []
        for i in range(0,len(value),100):
            subset = value[i:i+100]
            subavg = sum(subset)/len(subset)
            ypoints.append(subavg)
        print(len(ypoints))
        plt.subplot(row, col, idx)
        plt.xticks(range(0,len(ypoints),3))
        plt.yticks(range(0,30,2))
        plt.scatter(range(len(ypoints)), ypoints, s=10)
        plt.title(key)
        idx += 1
        # break
    # figure = plt.figure(figsize=(10,10))
    plt.savefig("fig_block_txs.jpg", dpi=200)
    plt.close()

def data_blocktxs(num_txs: dict):
    validvalues = {}
    datas = []
    for key, value in num_txs.items():
        alltxsnoignore = sum(value)
        data = key+": "+str(alltxsnoignore) + "\t"+ str(len(value))
        value = value[len(value)//3:len(value)//3*2]
        if len(value) == 0: continue
        alltxs = 0
        data2 = ""
        validvalues[key] = []
        for v in value:
            alltxs += int(v)
            validvalues[key].append(int(v))
            # data2 += "\t"+str(v)
        avg = alltxs/len(value) if len(value) > 0 else 0
        data += "\t" + str(alltxs) + "\t" + str(avg)
        data += data2
        datas.append(data+"\n") 
    datas.sort(key=cmp_to_key(compare))       
    with open("out_bt_txs.txt",'w') as f:
        f.writelines(datas)

def data_bt_interval(timestamps: dict):
    datas = []
    for key, value in timestamps.items():
        data = key + ":"
        for x in value:
            data += "\t" + str(x)
        data += "\n"
        datas.append(data)
    datas.sort(key=cmp_to_key(compare))       
    with open("out_bt_interval.txt",'w') as f:
        f.writelines(datas)
        

def data_parse():
    for expdir in dirs:
        if not expdir.startswith("bi"): continue
        path = os.path.join(basedir, expdir, "remote_log")
        if not os.path.exists(path): continue
        print(expdir)
        for logdir in os.listdir(path):
            log = os.path.join(path, logdir, "tendermint_0.log")
            if not os.path.exists(log):
                continue
            with open(log, 'r', encoding = 'utf-8') as f:
                text = f.read()
                num_txs[expdir] = []
                timestamps[expdir] = []
                for x in recp.findall(text):
                    num_txs[expdir].append(int(x[2]))
                    timestamps[expdir].append(
                        time.mktime(time.strptime("{} {}".format(x[0], x[1]), "%Y-%m-%d %H:%M:%S"))
                    )
            break
    json.dump(num_txs, open("out_raw_numtxs.json", 'w'))
    json.dump(timestamps, open("out_raw_timestamps.json", 'w'))
    # return num_txs, timestamps

def cost_sendblock(path):
    import re
    import numpy as np
    def analysis(path):
        with open(path, 'r') as f: text = f.read()
        result = re.findall("send block cost: (\d+), block", text)
        result = [int(x) for x in result]
        return np.mean(result)
    
    print(analysis(path))

if __name__ == "__main__":
    # data_parse()
    # numtxs = json.load(open("out_raw_numtxs.json", 'r'))
    # timestamps = json.load(open("out_raw_timestamps.json", 'r'))
    # fig_interval(timestamps=timestamps)
    cost_sendblock("yiiguo_scripts/output/sendtx_group_1656917711111/logs/bi15-pn200-bc30-rt005_sender.log")



    

