# 2022-03-31T11:00:54+08:00 INFO yiiguo time cost height=3 module=consensus propose=847964291 round=0
# docker logs container_name 2>&1 | python3 yiiguo_scripts/time_cost.py
import numpy as np
import sys
import re

time_cost_raw = []
time_cost_mean = 0
lines = []
lines = sys.stdin.readlines()

all_propose = []
all_prevote = []
all_precommit = []
all_commit = []
consensus_phase = {
    "propose": [],
    "prevote": [],
    "precommit": [],
    " commit": [] # 注意这个时间
}
for line in lines:
    if "Inf" not in line:
        for key, v in consensus_phase.items():
            values = re.findall(key+"=([0-9]+)\s", line)
            if len(values) > 0: consensus_phase[key].append(int(values[0]))

for key, v in consensus_phase.items():
    try:
        mean = int(np.mean(v))
    except:
        mean = 0
    print("phase {}, count: {}, mean: {}".format(key, len(v), mean))

