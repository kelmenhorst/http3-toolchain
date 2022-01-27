import sys
import argparse
import os
import json
import glob

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
    argparser.add_argument("-c", "--cummulate", help="cummulate", action='store_true')
    out = argparser.parse_args()

    steps = None
    if out.steps:
        steps = out.steps.split(" ")
        
    files = [out.file]
    if os.path.isdir(out.file):
        files = glob.glob(out.file+"/2*.json*")
    print("Processing files...", files, "\n")

    cummulation = []

    for f in files:
        fileID = f.split("/")[-1].split("_")[0]
        lines = []
        try:
            with gzip.open(f, 'r') as dump:
                lines = dump.readlines()
        except:
            with open(f, 'r') as dump:
                lines = dump.readlines()
        
        for l in lines:
            data = json.loads(l)
            if data["test_keys"]["failure"] is not None and "ssl" in data["test_keys"]["failure"]:
                print(data["input"], data["annotations"]["urlgetter_step"] , data["test_keys"]["failure"])
            continue
            if steps and  data["annotations"]["urlgetter_step"] not in steps:
                continue
            if out.inputurl is not None and not out.inputurl in data["input"]:
                continue
            if out.failure and data["test_keys"]["failure"] is None:
                continue
            if out.failuretype is not None and data["test_keys"]["failure"] is not None and not out.failuretype in data["test_keys"]["failure"]:
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
                    cummulation.append(data["input"])
            else:
                print(data["input"], data["annotations"]["urlgetter_step"], data["test_keys"]["failure"])
                print(" ")

    if out.cummulate:
        print(cummulation)

        
if __name__ == "__main__":
    main(sys.argv[1:])