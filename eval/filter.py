import sys
import argparse
import os
import json
import glob
import gzip

def main(arg):
    # Create the parser
    argparser = argparse.ArgumentParser(description='')

    # Add the arguments
    argparser.add_argument("-F", "--file", help="use specific input file", required=True)
    argparser.add_argument("-s", "--steps", help="name(s) of (two) urlgetter step(s) to investigate")
    argparser.add_argument("-u", "--inputurl", help="filter input url")
    argparser.add_argument("-ip", "--ip", help="filter input IPv4")
    argparser.add_argument("-t", "--failuretype", help="failure type")
    argparser.add_argument("-f", "--failure", help="failure", action='store_true')
    argparser.add_argument("-S", "--success", help="success", action='store_true')
    argparser.add_argument("-c", "--cummulate", help="cummulate", action='store_true')
    out = argparser.parse_args()

    steps = None
    if out.steps:
        steps = out.steps.split(" ")
        
    files = [out.file]
    if os.path.isdir(out.file):
        files = glob.glob(out.file+"/2*.json*")
    print("Processing files...", files, "\n")

    cummulation = {}

    for f in files:
        fileID = f.split("/")[-1].split("_")[0]
        lines = []
        try:
            with gzip.open(f, 'r') as dump:
                lines = dump.readlines()
        except:
            with open(f, 'r') as dump:
                lines = dump.readlines()
        
        for i,l in enumerate(lines):
            data = json.loads(l)
            step = data["annotations"]["urlgetter_step"]
            if i+1 < len(lines):
                next_data = json.loads(lines[i+1])
                # if the measurement was repeated, ignore this one
                if next_data["annotations"]["urlgetter_step"] == step:
                    continue
            if steps and step not in steps:
                continue
            if out.inputurl is not None and not out.inputurl in data["input"]:
                continue
            if out.failure and data["test_keys"]["failure"] is None:
                continue
            if out.success and data["test_keys"]["failure"] is not None:
                continue
            if out.failuretype is not None:
                if data["test_keys"]["failure"] is None:
                    continue
                if out.failuretype not in data["test_keys"]["failure"] and out.failuretype not in data["test_keys"]["failed_operation"]:
                    continue
            try:
                probed_ip = data["test_keys"]["queries"][0]["answers"][0]["ipv4"]
                if out.ip is not None and probed_ip != out.ip:
                    continue
            except:
                # print(data["input"], data["annotations"]["urlgetter_step"])
                continue 

            if out.cummulate:
                if data["input"] not in cummulation:
                    cummulation[data["input"]] = 1
                else:
                    cummulation[data["input"]] += 1
            else:
                print(data["input"], data["annotations"]["urlgetter_step"], data["test_keys"]["failure"], data["test_keys"]["failed_operation"])
                print(" ")

    if out.cummulate:
        print(cummulation)

        
if __name__ == "__main__":
    main(sys.argv[1:])