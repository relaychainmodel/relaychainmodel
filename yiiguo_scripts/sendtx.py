# curl -s 'localhost:26657/broadcast_tx_commit?tx="abcd"
import requests
import threading
import time
import sys
import os
import json
import loguru

logger = loguru.logger
logger.remove()
logger.add(os.path.join(os.path.dirname(__file__), 'log', 'sendtx.log'), mode="w")

dir_path = os.path.dirname(__file__)
resp_path = os.path.join(dir_path, "output_test", "sendtx_resp.txt")
costtime = {}

result = {}
host = "10.21.4.37"
# host = "127.0.0.1"

def query_by_rpc():
    result = requests.get(
        url='http://{}:26657/num_unconfirmed_txs'.format(host),
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
        url = 'http://{}:26657/tx?hash=0x{}'.format(host, txhash)    
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
    
    url = 'http://{}:26657/block?height={}'.format(host, height)    
    result = requests.get(url, headers={'Connection':'close'})
    try:
        info = json.loads(result.text)
    except Exception as e:
        return "", "getProposer exception: {}, height: {}".format(e, height)
        
    result = info.get('result', None)
    if result is not None:
        return info['result']['block']['header']['proposer_address'], ""        

def sendTx(idx):

    txnum_in_cs = 0
    txnum_in_cs, txnum_uncfm, err = query_by_rpc()
    if err != "":
        txnum_in_cs = -1
        txnum_uncfm = -1
        logger.error("query_by_rpc exception, error: {}".format(err))

    start_time = time.time_ns()    
    url = 'http://{}:26657/broadcast_tx_async?tx="{}-{}"'.format(host, int(time.time()*1000), idx)    
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
    costtime[idx] = {
        'idx': idx,
        'start': start_time,
        'cost': time.time_ns() - start_time,
        'block': block,
        'txhash': txhash,
        'proposer': proposer_address,
        'unconfirmd': txnum_uncfm,
        'incs': txnum_in_cs,
    }
    
thread_num = int(sys.argv[1])
threads = []

for i in range(thread_num):
    threads.append(
        threading.Thread(target=sendTx, args=(i,))
    )

start_time = time.time_ns()
for idx, thread in enumerate(threads):
    thread.start()
    print("start thread progress {}/{} ...".format(idx+1, len(threads)), end='')
    if idx != len(threads)-1:
        sys.stdout.write('\r')
    else:
        print()
print("send tx async ok!")
print("waiting...")
for idx, thread in enumerate(threads):
    thread.join()
    print("wait thread progress {}/{} ...".format(idx+1, len(threads)), end='')
    if idx != len(threads)-1:
        sys.stdout.write('\r')
    else:
        print()
print("send finished!")
logger.info("send finished!")

end_time = time.time_ns()
cost_time = end_time-start_time
with open(resp_path, 'w') as f:
    f.write("time cost: {}, send num: {}, tps: {}\n".format(cost_time, len(costtime), thread_num/cost_time))
    infos = ["{}\n".format(json.dumps(v)) for k,v in costtime.items()]
    # infos = sorted(infos, key=lambda x: x[0])
    f.writelines(infos)

    