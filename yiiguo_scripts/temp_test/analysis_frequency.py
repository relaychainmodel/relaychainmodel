import json
from matplotlib import pyplot as plt

path_item = "yiiguo_scripts/output/sendtx_group_1720472042842/bi600-pn20-bc25-rt025/output/process/1720472042840/item"
path_info = "yiiguo_scripts/output/sendtx_group_1720472042842/bi600-pn20-bc25-rt025/1720472042840"

datas_item = json.load(open(path_item, 'r'))
datas_info_by_txhash = {}
with open(path_info, 'r') as f:
    datas_info = [json.loads(line) for line in f.readlines()]
for info in datas_info:
    datas_info_by_txhash[info['txhash']] = info['start']

print(len(datas_item))

datas_item_ts = {}
for key, value in datas_item.items():
    datas_item_ts[key] = {
        'mempool': value['mempool'],
        'start': datas_info_by_txhash[key]
    }

axies = [(item['start'], item['mempool']) for item in datas_item_ts.values()]
x = [int(item[0]) for item in axies]
y = [int(item[1]) for item in axies]

plt.scatter(x,y)

plt.savefig("yiiguo_scripts/temp_test/frequency.jpg")