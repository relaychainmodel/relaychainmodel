"""
python yiiguo_scripts/process_batch.py --process_path=yiiguo_scripts/output/sendtx_group_1718991362281
"""
import os
import sys
import subprocess
import argparse
import json
from typing import List, Dict

def write_excel_format(outputs: Dict[str, List[Dict[str, float]]], dirpath: str):
    # keys =  ["broadcast","mempool","cs0","cs1","cs2","cs3","incs","uncfmd_all","uncfmd","block_real_size","tps","latency_in_tps","latency_overall"]
    keys =  ["broadcast","mempool","cs0","cs1","cs2","cs3","uncfmd_all","uncfmd","block_real_size","tps","latency_overall"]
    texts = []
    for k, v in outputs.items():
        try:
            for key in ["broadcast","mempool","cs0","cs1","cs2","cs3"]:
                v[0][key]=v[0][key]/1000000000
            col = ",".join([k]+[str(v[0][key]) for key in keys])
            texts.append(col)
        except KeyError:
            print('有一组未产出结果，请检查',k)
    print(texts)
    # 第一个2代表着是哪个指标，第二个是指指标的缩写占两个字符
    texts = sorted(texts, key=lambda x: int(x.split("-")[2][2:]))
    with open(os.path.join(dirpath, 'measured_results.txt'), 'w') as f:
        f.write("\n".join(texts))


def process_batch(dirpath: str):
    dirs = os.listdir(dirpath)
    alloutputs = {} # expargs: mean_dict
    for expdir in dirs:
        if expdir == 'logs':
            continue
        expdir = os.path.join(dirpath, expdir)
        if not os.path.isdir(expdir):
            continue
        paths = os.listdir(expdir)
        if len(paths) == 0:
            continue
        print("deal with expdir: {}".format(expdir))
        txfilenames = []
        for path in paths:
            abspath = os.path.join(expdir, path)
            if os.path.isfile(abspath):
                txfilenames.append(path)
        alloutputs[os.path.basename(expdir)] = []
        for txfilename in txfilenames:
            print("work for: {}".format(txfilename))
            processid = txfilename
            txfile = os.path.join(expdir, txfilename)
            logpath = os.path.join(expdir, 'remote_log', txfilename)
            for logfile in os.listdir(logpath):
                items = logfile.split('_')
                if len(items) < 3: continue
                newlog = 'tendermint_{}'.format(items[2])
                os.system('cp {} {}'.format(os.path.join(logpath, logfile), os.path.join(logpath, newlog)))
            outputpath = os.path.join(expdir, 'output', 'process')
            process_args = "--process_type=remote --process_id={} --process_tx_file={} --process_log_path={} --process_output_path={}".format(
                processid, txfile, logpath, outputpath
            )
            popen = subprocess.Popen(
                args=['python yiiguo_scripts/process.py {}'.format(process_args)],
                shell=True,
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            popen.wait()
            if popen.returncode != 0:
                raise Exception("process({}) error, returncode: {}, out: {}, err: {}".format(expdir, popen.returncode, popen.stderr.read().decode(), popen.stdout.read().decode()))
            print("process ok! exp: {}, expfile: {}".format(expdir, txfilename))
            alloutputs[os.path.basename(expdir)].append(json.load(open(os.path.join(outputpath, processid, 'mean'), 'r'))) 
    print("finished !!!")
    finalfile = os.path.join(dirpath, 'measured_results.json')
    json.dump(alloutputs,open(finalfile, 'w'))
    print("write all results to {} !!!".format(finalfile))
    write_excel_format(alloutputs, dirpath) 
    pass

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process_path", type=str)
    return parser.parse_args()

if __name__ == '__main__':
    args = getArgs()
    process_batch(args.process_path)
