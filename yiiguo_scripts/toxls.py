import argparse
import json
import os

def toxls(path: str):
    keys_exp = [
        "bi15-pn2-bc30-rt005",
        "bi15-pn5-bc30-rt005",
        "bi15-pn10-bc30-rt005",
        "bi15-pn20-bc30-rt005",
        "bi15-pn50-bc30-rt005",
        "bi15-pn75-bc30-rt005",
        "bi15-pn100-bc30-rt005",
        "bi15-pn150-bc30-rt005",
        "bi15-pn200-bc30-rt005",
        "bi15-pn10-bc30-rt1",
        "bi15-pn10-bc30-rt01",
        "bi15-pn10-bc30-rt001",
        "bi15-pn10-bc30-rt0001",
        "bi15-pn10-bc30-rt05",
        "bi15-pn10-bc30-rt025",
        "bi15-pn10-bc30-rt075",

    ]
    keys_idc = [
        "broadcast",
        "mempool",
        "cs0",
        "cs1",
        "cs2",
        "cs3",
        "incs",
        "uncfmd_all",
        "uncfmd"
    ]
    datas = json.load(open(os.path.join(path, "measured_results.json"), 'r'))
    results = []
    for key in keys_exp:
        data = datas.get(key, None)
        if data is None: continue
        for d in data:
            s = key
            for k in keys_idc:
                v = d[k]
                s += "  {:.2f}".format(v)
            results.append(s+"\n")
    with open(os.path.join(path, "measured_results_xls.txt"), 'w') as f:
        f.writelines(results)
    # json.dump(results, )

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process_path", type=str)
    return parser.parse_args()

if __name__ == '__main__':
    args = getArgs()
    toxls(args.process_path)

