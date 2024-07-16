"""
run experiments parallelly

各个指标在各自的进程上运行, 而不是线程

demo:
python yiiguo_scripts/master.py --group_num=5 --node_num=4 --init_config=n --init_progress=y
nohup python yiiguo_scripts/master.py --group_num=5 --node_num=10 --init_config=y --init_progress=y 2>&1 >yiiguo_scripts/log/master.out &
sh yiiguo_test/node_multi/remote/clear.sh all
"""
import enum
import json
import threading
import multiprocessing
import sendtx_para_random2 as sendtx
import argparse
import queue
import subprocess
import os
import time
from loguru import logger

HOST = ""


PARA_NUM = [20]
# PARA_NUM = [2,5,10,20,50,75,100,150,200]
# RATIO = [0.001,0.01,0.05,0.1,0.25,0.5,0.75,1]
RATIO=[0.25]
BLOCK_INTERVAL = [15]
# BLOCK_INTERVAL = [15]
# BLOCK_INTERVAL = [300,600]
# BLOCK_INTERVAL = [15]
BLOCK_CAP = [25]
# BLOCK_CAP = range(5,55,5)
# BLOCK_CAP = range(10,80,10)
RATIO_POINT = 500
BLOCKALL = 1000
CHECK_DELTA = 0.05

# all ports: 26400-26600
# each group: 26400-26409
# so maxium of tm node on each server is 5, each node needs 2 contiguous ports
# so maxium of tm group on each server is 20
PORT_HEAD = 26400 
PORT_TAIL = 26600
MAX_NODE = 5
MAX_GROUP = (PORT_TAIL-PORT_HEAD)/(2*MAX_NODE)
OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__),
    'output',
    'sendtx_group_{}'.format(int(time.time()*1000))
)
PROGRESS_FILE = os.path.join(
    os.path.dirname(__file__),
    '.progress'
)
class ProgressStatus:
    READY = 0
    WORKING = 1
    DONE = 2
threading_rlock = threading.RLock()
process_rlock = multiprocessing.RLock()

logger = logger.bind(expkey="master")
logger.remove()
logger.add(
    os.path.join(
        os.path.dirname(__file__),
        'log',
        'master.log'
    ),
    mode='w',
    filter=lambda record: record['extra']['expkey'] == 'master'
)

def get_exp_args():
    expargs = []
    # for rat in RATIO:
    #     expargs.append(
    #         {
    #             'para_num': 10,
    #             'block_interval': 15, 
    #             'block_cap': 30, 
    #             'ratio': rat
    #         }
    #     )
    for block_interval in BLOCK_INTERVAL:
        for block_cap in BLOCK_CAP:
            for ratio in RATIO:
                for para_num in PARA_NUM:
                    expargs.append(
                        {
                            'para_num': para_num,
                            'block_interval': block_interval, 
                            'block_cap': block_cap, 
                            'ratio': ratio
                        }   
                    )
    # expargs = [json.loads(x) for x in set([json.dumps(x) for x in expargs])]*10
    expargs = [
        json.loads(x) 
        for x in set([json.dumps(x) for x in expargs]) # 去重
    ]
    return expargs 

def update_progress(progress_id: int, info: dict, targetfile: str=PROGRESS_FILE):
    process_rlock.acquire()
    progress = json.load(open(targetfile, 'r'))
    if progress_id >= len(progress['args']):
        logger.error("update progress(size: {}), invalid id({})".format(len(progress['args']), progress_id))
        return 
    progress['args'][progress_id].update(info)
    logger.info("update progress: {}".format(info))
    json.dump(progress, open(targetfile, 'w'))
    process_rlock.release()

def gen_progress(exp_args: dict, exp_dir: str=OUTPUT_DIR):
    """
    progress = {
        'dir': '',
        'args': [
            {
                'status': 1, # 0: ready, 1: working, 2: done
                'arg': exp_args[0]
            },
            {
                'status': 1,
                'arg': exp_args[0]
            },
        ]
    }
    """
    progress = {
        'dir': exp_dir,
        'args': [
            {
                'status': ProgressStatus.READY,
                'arg': arg
            } for arg in exp_args
        ]
    }
    json.dump(progress, open(PROGRESS_FILE, 'w'))
    return progress



def get_tm_groups(group_num: int) -> queue.Queue:
    if group_num > MAX_GROUP:
        raise Exception("group num must be less than MAX_GROUP({})".format(MAX_GROUP))
        
    groups = multiprocessing.Manager().Queue(maxsize=group_num)
    for i in range(group_num):
        groups.put((
            i,
            PORT_HEAD+i*10
        ))
    return groups

def gen_config(node_num):
    popen = subprocess.Popen(
        "sh yiiguo_test/node_multi/remote/init.sh {}".format(node_num), 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    popen.wait()
    if popen.returncode != 0:
        logger.error("init node error, returncode: {}, out: {}, err: {}".format(popen.returncode, popen.stderr.read().decode(), popen.stdout.read().decode()))
        raise Exception("start docker error")
    logger.info("init node out: {}".format(popen.stdout.read().decode()))
    logger.info("init node ok!")

def restart_docker(group, expkey):
    # TODO 检查是否启动失败
    logger.info("start docker... key:{}".format(expkey))
    groupId, port = group
    popen = subprocess.Popen(
        "sh yiiguo_test/node_multi/remote/start_nobuild2.sh {} {}".format(groupId, port), 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    popen.wait()
    if popen.returncode != 0:
        logger.error("start docker error, returncode: {}, out: {}, err: {}".format(popen.returncode, popen.stderr.read().decode(), popen.stdout.read().decode()))
        raise Exception("start docker error")
    logger.info("start docker out: {}".format(popen.stdout.read().decode()))
    logger.info("docker start ok!")

def get_log(group, expkey, output_path):
    logger.info("get log... key:{}".format(expkey))
    groupId = group[0]
    output_name = str(os.path.basename(output_path)).split('.')[0]
    log_dir = os.path.join(os.path.dirname(output_path), "remote_log", output_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    popen = subprocess.Popen("sh yiiguo_test/node_multi/remote/get_log.sh {} {}".format(log_dir, groupId), 
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

def clear_containers():
    logger.info("clear containers... ")
    popen = subprocess.Popen("sh yiiguo_test/node_multi/remote/clear.sh all", 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    popen.wait()
    if popen.returncode != 0:
        logger.error("clear containers error, returncode: {}, out: {}, err: {}".format(popen.returncode, popen.stderr.read().decode(), popen.stdout.read().decode()))
        raise Exception("clear containers error")
    logger.info("clear containers out: {}".format(popen.stdout.read().decode()))
    logger.info("clear containers ok!")

def start(groups: queue.Queue, progress_id: int, output_dir: str, arg_item: dict):

    tm_group = groups.get(block=True)
    exp_arg = arg_item['arg']
    logger.info("docker group: {} for args={} ".format(tm_group, exp_arg))
    url = "{}:{}".format(HOST, tm_group[1]+1)
    sender = sendtx.Sender(
        url=url,
        expargs=exp_arg,
        blockall=BLOCKALL,
        ratio_point=RATIO_POINT,
        check_delta=CHECK_DELTA,
        outputdir=output_dir
    )
    waiter = sendtx.Waiter(
        url=url,
        outputdir=output_dir,
        expkey=sender.get_expkey()
    )

    restart_docker(tm_group, sender.get_expkey())
    que_tx = multiprocessing.Manager().Queue()
    proc_sender = multiprocessing.Process(
        target=sender.start,
        args=(que_tx,)
    )

    proc_waiter = multiprocessing.Process(
        target=waiter.start,
        args=(que_tx,)
    )

    proc_sender.start()
    proc_waiter.start()

    proc_sender.join()
    proc_waiter.join()
    
    get_log(tm_group, sender.get_expkey(), waiter.output_file)
    arg_item['status'] = ProgressStatus.DONE
    update_progress(progress_id=progress_id, info=arg_item)
    groups.put(tm_group, block=True)

def schedule(groups: queue.Queue, progress: dict):
    processes = []
    output_dir = progress['dir']
    # mng_prog = multiprocessing.Manager().dict()
    

    for progress_id, arg_item in enumerate(progress['args']):
        status = arg_item['status']
        if status == ProgressStatus.DONE:
            continue
        while groups.empty(): continue
        proc = multiprocessing.Process(
            target=start,
            args=(groups, progress_id, output_dir, arg_item)
        )
        processes.append(proc)
        proc.start()
        arg_item['status'] = ProgressStatus.WORKING
        update_progress(progress_id=progress_id, info=arg_item)

    for proc in processes:
        proc.join()
    
        
def master(group_num: int, node_num: int, init_config: bool, init_progress: bool):  
    logger.info("get exp args...")  
    exp_args = get_exp_args()
    logger.info("get exp args ok! size: {}".format(len(exp_args)))  

    if init_progress:
        logger.info("init progress args...")  
        progress = gen_progress(exp_args)
        logger.info("init progress ok! path: {}".format(len(exp_args)))  
    else:
        logger.info("read progress from file: {}".format(PROGRESS_FILE))
        if not os.path.exists(PROGRESS_FILE):
            raise Exception("progress file not exists! file: {}".format(PROGRESS_FILE))
        progress = json.load(open(PROGRESS_FILE, 'r'))

    logger.info("get tendermint docker groups...")
    tm_groups = get_tm_groups(group_num)
    logger.info("groups size: {}".format(tm_groups.qsize()))

    if init_config:
        logger.info("init {} node configs...".format(node_num))
        startime = time.time()
        gen_config(node_num)
        endtime = time.time()
        logger.info(f"init ok! dur: {endtime-startime}")
    else:
        logger.warning("ignore node_num and use old configs!")

    schedule(tm_groups, progress)

    clear_containers()

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group_num", type=int, default=1)
    parser.add_argument("--node_num", type=int, default=4)
    parser.add_argument("--init_config", type=str, default="y")
    parser.add_argument("--init_progress", type=str, default="y")
    return parser.parse_args()

if __name__=="__main__":
    args = getArgs()
    master(
        group_num=args.group_num,
        node_num=args.node_num,
        init_config=args.init_config=='y',
        init_progress=args.init_progress=='y',
    )