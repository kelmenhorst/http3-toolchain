#!/usr/bin/env python3
import subprocess
from urllib.parse import urlparse
import sys
import argparse
import random
import json

sni_cloudflare = {}
sni_cloudflare["sni_alt"] = "https://www.cloudflare.com"
sni_cloudflare["sni_alt_name"] = "www.cloudflare.com"
sni_cloudflare["sni_alt_cache"] = "104.16.124.96"

sni_other = {}
sni_other["sni_alt"] = "https://quic.nginx.org/"
sni_other["sni_alt_name"] = "quic.nginx.org"
sni_other["sni_alt_cache"] = "35.214.218.230"

def run_urlgetter_command(entry):
    cmd = make_urlgetter_command(entry)
    print("RUN ",cmd)
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out_str = out.stdout.decode("utf-8")
    return out_str

def run_quicping_command(entry):
    cmd = make_quicping_command(entry)
    print("RUN",cmd)
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out_str = out.stdout.decode("utf-8")
    return out_str

def measure(step, url):
    entry = {}
    entry["input_url"] = url
    entry["domain"] = urlparse(url).netloc

    proto, dnsoption = step.split("_")
    # protocol
    if proto == "quic":
        entry["http3"] = "true"
    elif proto == "tcp":
        entry["http3"] = "false"

    # DNS
    if dnsoption == "cached":
        entry["dnscache"] = dnscache[entry["domain"]]
    elif dnsoption == "local":
        entry["resolver_url"] = "dot://8.8.8.8:853"

    entry["step"] = step

    run_urlgetter_command(entry)
    return entry


def measure_sni(entry):
    sni = sni_other
    entry["step"] = entry["step"]+"_sni"
    entry["sni"] = sni["sni_alt_name"]
    out = run_urlgetter_command(entry)

    # cloudflare QUIC rejects non-cloudflare SNIs. 
    # If we encounter such an error we retry with the cloudflare SNI.
    try:
        with open("report.jsonl", 'r') as dump:
            lastline = dump.readlines()[-1]
        data = json.loads(lastline)
        input_url = data["input"]
        failure = data["test_keys"]["failure"]
        if "ssl_failed_handshake" in failure or "tls: handshake failure" in failure:
            sni = sni_cloudflare
            entry["sni"] = sni["sni_alt_name"]
            out = run_urlgetter_command(entry)
    except:
        pass

    entry["step"] = entry["step"]+"_inverse"
    entry["sni"] = entry["domain"]
    entry["input_url"] = sni["sni_alt"]
    entry["domain"] = urlparse(sni["sni_alt"]).netloc
    if "dnscache" in entry:
        entry["dnscache"] = sni["sni_alt_cache"]
    run_urlgetter_command(entry)


def measure_quicping(entry):
    out = run_quicping_command(entry)
    

     
def make_urlgetter_command(entry):
    cmd = [miniooni]

    cmd.append("-i")
    cmd.append(entry["input_url"])

    cmd.append("-O")
    cmd.append("HTTP3Enabled="+entry["http3"])

    if "resolver_url" in entry:
        cmd.append("-O")
        cmd.append("ResolverURL="+entry["resolver_url"])
        cmd.append("-O")
        cmd.append("RejectDNSBogons=true")
    
    if "dnscache" in entry:
        cmd.append("-O")
        cmd.append("DNSCache="+entry["domain"]+" "+entry["dnscache"])
    
    if "sni" in entry:
        cmd.append("-O")
        cmd.append("TLSServerName="+entry["sni"])
        cmd.append("-O")
        cmd.append("NoTLSVerify=true")
    
    cmd.append("-A")
    cmd.append("urlgetter_step="+entry["step"])

    cmd.append("-n") # no collector
    
    if "no_report" in entry:
        cmd.append("-N")

    cmd.append("urlgetter")
    return cmd

def make_quicping_command(entry):
    cmd = [miniooni]

    cmd.append("-i")
    if "dnscache" in entry:
        cmd.append(entry["dnscache"])
    else:
        cmd.append(entry["input_url"])
    
    cmd.append("-O")
    cmd.append("Repetitions=2")

    cmd.append("-A")
    cmd.append("measurement_url="+entry["input_url"])

    cmd.append("-n") # no collector
    
    if "no_report" in entry:
        cmd.append("-N")

    cmd.append("quicping")
    return cmd


def main(urls, dnscache, longm):
    sni_measure_input_quic = {}
    sni_measure_input_tcp = {}
    quicping_measure_input = {}
    all_quic = {}
    all_tcp = {}

    # first loop: test urls with local quad8
    tt = len(urls)
    c = 1
    if longm:
        for u in urls:
            print(str(c)+"/"+str(tt))
            c += 1

            # QUIC
            entry = measure("quic_local",u)

            # TCP
            entry = measure("tcp_local",u)
    
    # second loop: test urls with cached ip
    c = 1
    for u in urls:
        print(str(c)+"/"+str(tt))
        c += 1

        # QUIC
        entry = measure("quic_cached",u)
        all_quic[u] = entry

        # TCP
        entry = measure("tcp_cached",u)
        all_tcp[u] = entry
    
    try:
        with open("report.jsonl", 'r') as dump:
            lines = dump.readlines()

        for i,l in enumerate(lines):
            data = json.loads(l)
            input_url = data["input"]
            
            failure = data["test_keys"]["failure"]
            if failure is not None:
                step = data["annotations"]["urlgetter_step"]
                if "quic" in step:
                    quicping_measure_input[input_url] = all_quic[input_url].copy()
                    sni_measure_input_quic[input_url] = all_quic[input_url]
                else:
                    sni_measure_input_tcp[input_url] = all_tcp[input_url]
    except:
        pass


    tt = len(sni_measure_input_quic)
    c = 1
    for i, entry in sni_measure_input_quic.items():
        print("Retry failed websites with spoofed SNI (HTTP/3) "+ str(c)+"/"+str(tt))
        measure_sni(entry)
        c += 1
    
    tt = len(sni_measure_input_tcp)
    c = 1
    for i, entry in sni_measure_input_tcp.items():
        print("Retry failed websites with spoofed SNI (HTTPS) "+ str(c)+"/"+str(tt))
        measure_sni(entry)
        c += 1
    
    tt = len(quicping_measure_input)
    c = 1
    for i, entry in quicping_measure_input.items():
        print("Last round: Retry failed hosts with quicping "+ str(c)+"/"+str(tt))
        measure_quicping(entry)
        c += 1
        
            

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='Run script for urlgetter TCP/QUIC measurements.')

    # Add the arguments.
    argparser.add_argument("-u", "--urls", help="url list with resolved IPs (per line: url-----ip)", required=True)
    argparser.add_argument("-p", "--miniooni_path", help="path to miniooni executable", required=True)
    argparser.add_argument("-l", "--long", help="the long measurement tries local DNS resolution with Google DNS", action='store_true')
    out = argparser.parse_args()

    miniooni = out.miniooni_path

    # read urls
    urls = []
    dnscache = {}
    endpoints = {}
    with open(out.urls, "r") as urls_file:
        for l in urls_file:
            url, ip = l.strip().split("-----")
            urls.append(url)
            domain = urlparse(url).netloc
            dnscache[domain] = ip
            endpoints[ip] = None

    random.shuffle(urls)
    main(urls, dnscache, out.long)