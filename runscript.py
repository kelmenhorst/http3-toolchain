#!/usr/bin/env python3
import subprocess
from urllib.parse import urlparse
import sys
import argparse
import random


# read the input urls file and put them in a list

# TODO remove -n -N

# miniooni = "/home/kelmenhorst/fellowship/release/probe-cli-3.13.0/internal/miniooni"
sni_alt = "https://www.cloudflare.com"
sni_alt_name = "www.cloudflare.com"
sni_alt_cache = "104.16.124.96"

def run_command(entry):
    cmd = make_urlgetter_command(entry)
    print("RUN ",cmd)
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out_str = out.stdout.decode("utf-8")
    return out_str

def measurement_passed(output):
    if "<warn> measurement failed" in output:
        return False
    return True

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

    out = run_command(entry)
    return measurement_passed(out), entry


def measure_sni(step, entry):
    entry["step"] = entry["step"]+"_sni"
    entry["sni"] = sni_alt_name
    run_command(entry)

    entry["step"] = entry["step"]+"_inverse"
    entry["sni"] = entry["domain"]
    entry["input_url"] = sni_alt
    entry["domain"] = urlparse(sni_alt).netloc
    if "dnscache" in entry:
        entry["dnscache"] = sni_alt_cache
    run_command(entry)

     
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


def main(urls, dnscache, longm):
    sni_measure_input = {}
    keyidx = 0
    # first loop: test urls with local quad8
    tt = len(urls)
    c = 1
    if longm:
        for u in urls:
            print(str(c)+"/"+str(tt))
            c += 1

            # QUIC
            passed, entry = measure("quic_local",u)
            if not passed:
                sni_measure_input[keyidx] = dict(entry)
                keyidx += 1

            # TCP
            passed, entry = measure("tcp_local",u)
            if not passed:
                sni_measure_input[keyidx] = dict(entry)
                keyidx += 1
    
    # second loop: test urls with cached ip
    c = 1
    for u in urls:
        print(str(c)+"/"+str(tt))
        c += 1

        # QUIC
        passed, entry = measure("quic_cached",u)
        if not passed:
            sni_measure_input[keyidx] = dict(entry)
            keyidx += 1

        # TCP
        passed, entry = measure("tcp_cached",u)
        if not passed:
            sni_measure_input[keyidx] = dict(entry)
            keyidx += 1
    
    tt = len(sni_measure_input)
    for c, entry in sni_measure_input.items():
        print("Last round: Retry failed websites with spoofed SNI "+ str(c+1)+"/"+str(tt))
        measure_sni(entry["step"], entry)
        
            

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