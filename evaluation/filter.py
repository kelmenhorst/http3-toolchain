import sys
import argparse
import os
import json
import glob
import gzip
from measurement import Measurement, URLGetterMeasurement, QuicpingMeasurement
from eval import get_ipinfo


STEPS = {}

def add(datastructure, item):
    if type(datastructure) is dict:
        if item in datastructure:
            datastructure[item] += 1
            return
        datastructure[item] = 1
        return
    if type(datastructure) is list:
        datastructure.append(item)
        return

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
        if len(self.steps[ms]) == 0:
            return True

        mf = measurement.error_type().lower()
        if "failure" in self.steps[ms] and measurement.failure is None:
            return False
        if "success" in self.steps[ms] and measurement.failure is not None:
            return False
        if not (mf in self.steps[ms] or (measurement.failure is not None and "failure" in self.steps[ms])):
            return False
        if self.AND:
            for s in self.steps:
                if s == ms:
                    continue
                try:
                    omeasurement = STEPS[s][measurement.id]
                    of = omeasurement.error_type().lower()
                    if "failure" in self.steps[s] and omeasurement.failure is None:
                        return False
                    if "success" in self.steps[s] and omeasurement.failure is not None:
                        return False
                    if not (of in self.steps[s] or (omeasurement.failure is not None and "failure" in self.steps[s])):
                        return False
                except KeyError as e:
                    return False
                # if not (STEPS[s][measurement.id].error_type() in self.steps[s] or (STEPS[s][measurement.id].failure is not None and "failure" in self.steps[s])):
                #     return False
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
        for u in self.urls:
            if measurement.input_url in u or u in measurement.input_url:
                return True
        return False

class protofilter:
    def __init__(self, p):
        self.proto = None
        if p is not None:
            self.proto = p
    
    def filter(self, measurement):
        if self.proto is None:
            return True
        if self.proto == measurement.proto: 
            return True
        return False

class asnfilter:
    def __init__(self, a):
        self.asn = None
        if a is not None:
            self.asn = a
    
    def filter(self, measurement):
        if self.asn is None:
            return True
        if self.asn == measurement.probe_asn: 
            return True
        # print(measurement.probe_asn)
        return False

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
    unstable_hosts = {}
    if out.sanitycheck:
        lines = []
        with open(out.sanitycheck, "r") as scheck:
            lines = scheck.readlines()
        for l in lines:
            data = json.loads(l)
            if data["test_name"] == "quicping":
                continue
            if data["test_keys"]["failure"] is not None and not ("cloudflare" in data["input"] or "quic.nginx.org" in data["input"] or "plus.im" in data["input"]):
                unstable_hosts[data["input"]] = True
    print("Unstable hosts:", unstable_hosts.keys())

    step_filter = stepfilter(out.steps)
    url_filter = urlfilter(out.inputurl)
    ip_filter = ipfilter(out.ip)
    proto_filter = protofilter(out.proto)
    asn_filter = asnfilter(out.asn)
    server_filter = serverfilter(out.server)  
    filters = [step_filter, url_filter, ip_filter, server_filter, proto_filter, asn_filter]
    
    files = [out.file]
    if os.path.isdir(out.file):
        files = glob.glob(out.file+"/*.jsonl*")
    print("Processing files...", files, "\n")

    cummulate = False
    if out.dict:
        cummulation = {}
        cummulate = True
    if out.list:
        cummulation = []
        cummulate = True


    for f in files:
        fileID = f.split("/")[-1]
        lines = []
        try:
            with gzip.open(f, 'r') as dump:
                lines = dump.readlines()
        except:
            with open(f, 'r') as dump:
                lines = dump.readlines()
        
        for i,l in enumerate(lines):
            data = json.loads(l)
            if i+1 < len(lines):
                next_data = json.loads(lines[i+1])

            measurement = None
            id = Measurement.mID(data, fileID, data["input"])
            if data["test_name"] == "urlgetter":
                measurement = URLGetterMeasurement(data, id)
            elif data["test_name"] == "quicping":
                id = Measurement.mID(data, fileID,data["annotations"]["measurement_url"])
                measurement = QuicpingMeasurement(data, id)
            else:
                measurement = Measurement(data, id)

            if measurement.input_url in unstable_hosts:
                continue
            if measurement.step not in STEPS:
                STEPS[measurement.step] = {}
            STEPS[measurement.step][id] = measurement

       
    for k,step in STEPS.items():
        for id, measurement in step.items():    
            if not pass_filters(filters, measurement):
                continue

            if out.failure and measurement.failure is None:
                continue

            if out.success and measurement.failure is not None:
                continue
        
            if out.runtime and measurement.runtime < float(out.runtime):
                continue

            if out.failuretype is not None:
                if measurement.failure is None:
                    continue
                if out.failuretype not in measurement.failure and out.failuretype not in measurement.failed_op:
                    continue


            if cummulate:
                add(cummulation, measurement.input_url)
        
            else:
                print(measurement.input_url, measurement.step, measurement.failure, measurement.time, measurement.runtime)
                stats = measurement.read_write_stats()
                print(stats[0]["read_bytes"], stats[0]["read_count"])
                print(stats[0]["time_to_last_read_ok"])
                print(" ")

    if cummulate:
        print(cummulation, len(cummulation))
        return cummulation
    
    return None

        
if __name__ == "__main__":
    # Create the parser
    argparser = argparse.ArgumentParser(description='')

    # Add the arguments
    argparser.add_argument("-F", "--file", help="use specific input file", required=True)
    argparser.add_argument("-s", "--steps", help="name(s) of (two) urlgetter step(s) to investigate, add failure filter with '#', e.g. -s quic_cached#success")
    argparser.add_argument("-u", "--inputurl", help="filter input url")
    argparser.add_argument("-p", "--proto", help="filter protocol")
    argparser.add_argument("-a", "--asn", help="filter asn")
    argparser.add_argument("-ip", "--ip", help="filter input IPv4")
    argparser.add_argument("-t", "--failuretype", help="failure type")
    argparser.add_argument("-f", "--failure", help="failure", action='store_true')
    argparser.add_argument("-S", "--success", help="success", action='store_true')
    argparser.add_argument("-d", "--dict", help="cummulate to dictionary", action='store_true')
    argparser.add_argument("-l", "--list", help="cummulate to list", action='store_true')
    argparser.add_argument("-m", "--server", help="the response server, e.g. Litespeed")
    argparser.add_argument("-c", "--sanitycheck", help="report file with sanity check measurement")
    argparser.add_argument("-T", "--runtime", help="limit the runtime")
    out = argparser.parse_args()
    main(out)
