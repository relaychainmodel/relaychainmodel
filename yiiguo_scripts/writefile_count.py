# ("yiiguo writefile_txs", "txs_num", txs_num, "timestamp", time.Now().Local().UnixNano())
# docker logs container_name 2>&1 | python3 yiiguo_scripts/time_cost.py
import numpy as np
import sys
import re

time_cost_raw = []
time_cost_mean = 0
lines = []
lines = sys.stdin.readlines()
lines = lines[1:]
if len(lines) % 2 == 1:
    lines = lines[:len(lines)-1]

for idx in range(0,len(lines),2):
    line = lines[idx]
    if "Inf" in line:
        break
    values_init = re.findall('timestamp=([0-9]+)\s', line)
    if len(values_init) > 0:
        init = int(values_init[0])
    values_ok = re.findall('timestamp=([0-9]+)\s', lines[idx+1])
    if len(values_ok) > 0:
        ok = int(values_ok[0])
    time_cost_raw.append(ok-init)

try:
    mean = int(np.mean(time_cost_raw))
except:
    mean = 0
print("mean: {}".format(mean))

