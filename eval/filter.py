import sys
import argparse
import os
import json
import glob
import gzip
from measurement import Measurement, URLGetterMeasurement, QuicpingMeasurement


STEPS = {}

class stepfilter:
    def __init__(self, f):
        self.steps = {}
        self.AND = False
        if f is None:
            return
        if "&" in f:
            steps = f.split("&")
            self.AND = True
        else :
            steps = f.split("|")
     
        for s in steps:
            step_filters = s.split("#")
            step = step_filters[0].lower()
            self.steps[step] = []
            if len(step_filters) <= 1:
                continue
            for i in step_filters[1:]:
                self.steps[step].append(i.lower())

    def filter(self, measurement):
        if len(self.steps) == 0:
            return True
        ms = measurement.step.lower()
        if ms not in self.steps:
            return False
        mf = measurement.error_type().lower()
        if "failure" in self.steps[ms] and measurement.failure is not None:
            return True
        if len(self.steps[ms]) and mf not in self.steps[ms]:
            return False
        if self.AND:
            for s in self.steps:
                if s == ms:
                    continue
                if not (STEPS[s][measurement.id].error_type() in self.steps[s] or (STEPS[s][measurement.id].failure is not None and "failure" in self.steps[s])):
                    return False
        return True

class urlfilter:
    def __init__(self, f):
        self.urls = None
        if f is not None:
            self.urls = f.split(" ")
    
    def filter(self, measurement):
        if self.urls is None:
            return True
        if measurement.input_url == "https://www.cloudflare.com" or measurement.input_url == "https://quic.nginx.org/":
            return False
        return measurement.input_url in self.urls

class ipfilter:
    def __init__(self, f):
        self.ips = None
        if f is not None:
            self.ips = f.split(" ")
    
    def filter(self, measurement):
        if self.ips is None:
            return True
        return measurement.probe_ip in self.ips

class serverfilter:
    def __init__(self, f):
        self.servers = None
        if f is not None:
             self.servers = [s.lower() for s in f.split(" ")]    
    
    def filter(self, measurement):
        if self.servers is None:
            return True
        return measurement.get_server() in self.servers

def pass_filters(filters, measurement):
    for f in filters:
        if not f.filter(measurement):
            return False
    return True

def main(out):
    step_filter = stepfilter(out.steps)
    url_filter = urlfilter(out.inputurl)
    ip_filter = ipfilter(out.ip)
    server_filter = serverfilter(out.server)  
    filters = [step_filter, url_filter, ip_filter, server_filter]
    
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
            measurement = None
            id = Measurement.mID(data, fileID, data["input"])
            if out.experiment.lower() == "urlgetter":
                measurement = URLGetterMeasurement(data, id)
            elif out.experiment.lower() == "quicping":
                measurement = QuicpingMeasurement(data, id)
            else:
                measurement = Measurement(data, id)

            if measurement.step not in STEPS:
                STEPS[measurement.step] = {}
            STEPS[measurement.step][id] = measurement

            if i+1 < len(lines):
                next_data = json.loads(lines[i+1])
                # if the measurement was repeated, ignore this one
                if next_data["annotations"]["urlgetter_step"] == measurement.step:
                    continue
            
            if not pass_filters(filters, measurement):
                continue

            if out.failure and measurement.failure is None:
                continue

            if out.success and measurement.failure is not None:
                continue

            if out.failuretype is not None:
                if measurement.failure is None:
                    continue
                if out.failuretype not in measurement.failure and out.failuretype not in measurement.failed_op:
                    continue


            if out.cummulate:
                if measurement.input_url not in cummulation:
                    cummulation[measurement.input_url] = 1
                else:
                    cummulation[measurement.input_url] += 1
            else:
                print(measurement.input_url, measurement.step, measurement.failure, measurement.failed_op)
                print(" ")

    if out.cummulate:
        print(cummulation)
        return cummulation
    
    return None

        
if __name__ == "__main__":
    # Create the parser
    argparser = argparse.ArgumentParser(description='')

    # Add the arguments
    argparser.add_argument("-F", "--file", help="use specific input file", required=True)
    argparser.add_argument("-s", "--steps", help="name(s) of (two) urlgetter step(s) to investigate, add failure filter with '#', e.g. -s quic_cached#success")
    argparser.add_argument("-u", "--inputurl", help="filter input url")
    argparser.add_argument("-ip", "--ip", help="filter input IPv4")
    argparser.add_argument("-t", "--failuretype", help="failure type")
    argparser.add_argument("-f", "--failure", help="failure", action='store_true')
    argparser.add_argument("-S", "--success", help="success", action='store_true')
    argparser.add_argument("-c", "--cummulate", help="cummulate", action='store_true')
    argparser.add_argument("-m", "--server", help="the response server, e.g. Litespeed")
    argparser.add_argument("-e", "--experiment", help="the ooni experiment name", required=True)
    out = argparser.parse_args()
    main(out)
