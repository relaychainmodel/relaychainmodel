
import time

def test_startdocker():
    import subprocess
    popen = subprocess.Popen("sh yiiguo_test/node_multi_remote/start_nobuild.sh 4", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(popen.returncode)
    popen.wait()
    print(popen.returncode)
    print("out", popen.stdout.read().decode())
    print("err", popen.stderr.read().decode())

def test_getlog():
    import subprocess
    popen = subprocess.Popen("sh yiiguo_test/node_multi_remote/get_log.sh yiiguo_scripts/output/sendtx_para_random_output_old/pn2-bi15-bc30-rt005/remote_logs", 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    print(popen.returncode)
    popen.wait()
    print(popen.returncode)
    print("out", popen.stdout.read().decode())
    print("err", popen.stderr.read().decode())

def test_funcargs():
    def func(a, b, c):
        print(a,b,c)
    s = {'a':1,'b':2,'c':3}
    func(**s)

def test_load():
    import requests
    import threading
    import json
    count = 1
    hosts = [
        "10.21.4.37:26401",
        "10.21.4.37:26411",
        "10.21.4.37:26421",
        "10.21.4.37:26431",
        "10.21.4.37:26441",
    ]
    def send(idx: int, host: str, cnt: int):
        rpc = 'http://{}/num_unconfirmed_txs'.format(host)
        try:
            result = requests.get(rpc, headers={'Connection':'close'})
            if result.status_code != 200:
                print(result.status_code, result.text)
            result.close()
        except Exception as e:
            print("Error num_unconfirmed_txs(idx: {}, tx: {}): {}".format(idx, cnt, e))
            return

        rpc = 'http://{}/broadcast_tx_async?tx="{}-{}"'.format(host, time.time_ns(), idx)
        try:
            result = requests.get(rpc, headers={'Connection':'close'})
            if result.status_code != 200:
                print(result.status_code, result.text)
            txhash = json.loads(result.text)['result']['hash']
            result.close()
        except Exception as e:
            print("Error broadcast_tx_async(idx: {}, tx: {}): {}".format(idx, cnt, e))
            return

        while True:
            rpc = 'http://{}/tx?hash=0x{}'.format(host, txhash)
            try:
                result = requests.get(rpc, headers={'Connection':'close'})
                if result.status_code == 200:
                    break
                time.sleep(0.1)
                result.close()
            except Exception as e:       
                print("Error wait tx(idx: {}, tx: {}): {}".format(idx, cnt, e))
            
    def loop_send(idx: int):
        host = hosts[idx%len(hosts)]
        loop_time = 0
        threads = []
        cnt = 0
        while True:
            
            for i in range(30):
                threads.append(
                    threading.Thread(target=send, args=("{}-{}".format(idx, i), host, cnt))
                )
                threads[-1].start()
                cnt += 1
            loop_time += 1
            if loop_time >= 10000:
                for thread in threads:
                    thread.join()
                print("thread-{} ok! loop_time: {}".format(idx, loop_time))
                break
            if loop_time%500 == 0:
                print("thread-{}, process: {}".format(idx, loop_time))
            time.sleep(0.01)
        
            
            
    threads = []
    for i in range(count):
        threads.append(
            threading.Thread(target=loop_send, args=(i, ), name=str(i))
        )
        threads[-1].start()
    for thread in threads:
        thread.join()
        



    
    


if __name__ == '__main__':
    # test_getlog()
    # test_funcargs()
    test_load()
