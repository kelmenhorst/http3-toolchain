import json
import sys
import os
import glob
import argparse
import gzip
import sys
import pandas as pd
from datetime import datetime
import numpy as np
from consistency import consistency
from measurement import Measurement, URLGetterMeasurement
from sankey import sankey

import ipinfo
access_token = 'c896c6da34ef96'
handler = ipinfo.getHandler(access_token)

timestamp_fmt = '%Y-%m-%d %H:%M:%S'

def get_ipinfo(ip):
	return handler.getDetails(ip)


def conditional_eval(data_t, data_q, evaluation):
	failures = [v.error_type() for (k,v) in data_t.items() if v.failure is not None]
	u_failures = list(dict.fromkeys(failures))
	u_failures.append("success")

	evaluation["conditional_eval"] = {}

	for f in u_failures:
		q_errors = {}
		print("\n"+f, failures.count(f))
		evaluation["conditional_eval"][f] = {}
		evaluation["conditional_eval"][f]["n"] = failures.count(f)

		for id, d in data_t.items():
			if d.error_type() == f:
				try:
					print("---", data_q[id].error_type(), data_t[id].failed_op, data_q[id].failed_op)
					qn = q_errors.get(data_q[id].error_type(),[])
					ipinfo = get_ipinfo(data_q[id].probe_ip)
					qn.append(data_q[id].input_url+" "+data_q[id].probe_ip + " "+ ipinfo.country + " " + ipinfo.org + str(data_q[id].tk["requests"][-1]["response"]["code"]))
					q_errors[data_q[id].error_type()] = qn
					print(data_q[id].get_server())
					
				except KeyError as e:
					pass
		
		evaluation["conditional_eval"][f]["step_2"] = q_errors
	return evaluation


def only_err(data_1, data_2):
	failure_keys_1 = [k for (k,v) in data_1.items() if v.failure is not None]
	failure_keys_2 = [k for (k,v) in data_2.items() if v.failure is not None]

	merged_keys = failure_keys_1
	for k in failure_keys_2:
		if k not in merged_keys:
			merged_keys.append(k)
	
	return {k:v for (k,v) in data_1.items() if k in merged_keys}, {k:v for (k,v) in data_2.items() if k in merged_keys}



def main(arg):
	# Create the parser
	argparser = argparse.ArgumentParser(description='Visualizes correlation of two experiment steps.')

	# Add the arguments
	argparser.add_argument("-F", "--file", help="use specific input file", required=True)
	argparser.add_argument("-s", "--steps", help="name(s) of (two) urlgetter step(s) to investigate", required=True)
	argparser.add_argument("-o", "--outpath", help="path to store the output plot file")
	argparser.add_argument("-e", "--onlyerrors", help="only consider failure cases", action="store_true")
	argparser.add_argument("-a", "--asn", help="asn")
	argparser.add_argument("-c", "--sanitycheck", help="report file with sanity check measurement")
	out = argparser.parse_args()

	outpath = out.outpath
	if outpath is None:
		outpath = "."

	steps = out.steps.split(" ")

	unstable_hosts = {}
	if out.sanitycheck:
		lines = []
		with open(out.sanitycheck, "r") as scheck:
			lines = scheck.readlines()
		for l in lines:
			data = json.loads(l)
			if data["test_keys"]["failure"] is not None and not "cloudflare" in data["input"]:
				unstable_hosts[data["input"]] = True
	print("Unstable hosts:", unstable_hosts.keys())

	evaluation = {}

		
	files = [out.file]
	if os.path.isdir(out.file):
		files = glob.glob(out.file+"/*.json*")
	print("Processing files...", files, "\n")

	possible_asns = {}


	inputs = {}
	dicts = {}
	min_time_stamp = None
	max_time_stamp = None
	for step in steps:
		dicts[step] = {}

	for f in files:
		if "_evaluation.json" in f:
			continue
		if "sanity" in f or "oldlist" in f:
			continue
		fileID = f.split("/")[-1][0:8]
		print(fileID)
		lines = []
		try:
			with gzip.open(f, 'r') as dump:
				lines = dump.readlines()
		except:
			with open(f, 'r') as dump:
				lines = dump.readlines()
		
		for i,l in enumerate(lines):
			data = json.loads(l)
			
			possible_asns[data["probe_asn"]] = True
			
			if out.asn and data["probe_asn"] != out.asn:
				continue
			if not "urlgetter_step" in data["annotations"]:
				continue
			
			try:
				probed_ip = data["test_keys"]["queries"][0]["answers"][0]["ipv4"]
			except:
				# print(data["input"], data["annotations"]["urlgetter_step"])
				continue
			
			step = data["annotations"]["urlgetter_step"]
			if i+1 < len(lines):
				next_data = json.loads(lines[i+1])
				# if the measurement was repeated, ignore this one
				if next_data["annotations"]["urlgetter_step"] == step:
					continue

			if not ("_inverse" in step):
				url_ = data["input"]
			if url_ in unstable_hosts:
				continue
			

			# mID = fileID + "-" + url_ + data["probe_asn"] + data["test_name"]
			mID = Measurement.mID(data, fileID, url_)
			msrmnt = URLGetterMeasurement(data, mID)
			
			# disregard DNS failures
			if msrmnt.failed_op == "resolve":
				continue
			if msrmnt.step not in dicts:
				continue
			if mID in dicts[msrmnt.step]:
				# print("already in dict", mID, data["measurement_start_time"], dicts[msrmnt.step][mID].data["measurement_start_time"], msrmnt.failure, dicts[msrmnt.step][mID].failure)
				continue

			dicts[msrmnt.step][mID] = msrmnt

			tstamp = datetime.strptime(data["measurement_start_time"], timestamp_fmt)
			if max_time_stamp is None or tstamp > max_time_stamp:
				max_time_stamp = tstamp
			if min_time_stamp is None or tstamp < min_time_stamp:
				min_time_stamp = tstamp
			if msrmnt.step == steps[0]:
				if url_ not in inputs:
					inputs[url_] = [data["measurement_start_time"]]
				else:
					inputs[url_].append(data["measurement_start_time"])

	outpath = os.path.join(outpath, out.asn + "_" + steps[0] + "_" + steps[1])
	if out.sanitycheck:
		outpath += "_checked"


	evaluation["test_list"] = inputs
	evaluation["test_list_length"] = len(inputs.keys())
	evaluation["asn"] = list(possible_asns.keys())
	evaluation["time_span"] = [min_time_stamp, max_time_stamp]

	

	for v,d in dicts.items():
		frate = {k:v for (k,v) in d.items() if v.failure is not None}
		print("failures in step", v+":", len(frate), "/", len(d))
		failures = [v.error_type() for v in frate.values()]
		u_failures = list(dict.fromkeys(failures))

		evaluation[v] = {
			"n": len(d),
			"failed": len(frate),
			"failure_rate": len(frate)/float(len(d)),
		}

		for f in u_failures:
			q_errors = {}
			print("--",f, failures.count(f))

	if len(steps) == 1:
		sys.exit()
	
	dict_1, dict_2 = dicts.values()
	if out.onlyerrors:
		dict_1, dict_2 = only_err(dict_1, dict_2)

	evaluation = conditional_eval(dict_1, dict_2, evaluation)
	evaluation = sankey(steps, dict_1, dict_2, outpath, evaluation)

	# consistency(dict_1, dict_2)

	with open(outpath +"_evaluation.json", "w") as e:
		json.dump(evaluation, e, indent=4, sort_keys=True, default=str)


		
if __name__ == "__main__":
	main(sys.argv[1:])