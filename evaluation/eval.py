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
from measurement import Measurement, URLGetterMeasurement, QuicpingMeasurement
from sankey import sankey
from timing import time_of_day

import ipinfo
access_token = 'c896c6da34ef96'
handler = ipinfo.getHandler(access_token)

timestamp_fmt = '%Y-%m-%d %H:%M:%S'

class MeasurementCollector:
	def __init__(self, c, keys):
		self.classifier = c
		self.collection = {}
		for k in keys:
			self.collection[k] = {}

	def add_by_ID(self, measurement):
		key = getattr(measurement, self.classifier)
		self.collection[key][measurement.id] = measurement

	def has_key(self, measurement):
		key = getattr(measurement, self.classifier)
		return key in self.collection

	def has_id(self, id, measurement):
		key = getattr(measurement, self.classifier)
		return id in self.collection[key]
	
	def class_items(self):
		return self.collection.items()

	def classes(self):
		return self.collection.values()
	
	def classifiers(self):
		return self.collection.keys()



def get_ipinfo(ip):
	return handler.getDetails(ip)


def conditional_eval(data_t, data_q, evaluation):
	failures = [v.error_type() for (k,v) in data_t.items() if v.failure is not None]
	u_failures = list(dict.fromkeys(failures))

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
					qn.append(data_q[id].input_url+" "+data_q[id].probe_ip)
					q_errors[data_q[id].error_type()] = qn
					
				except KeyError as e:
					pass
		
		evaluation["conditional_eval"][f]["step_2"] = q_errors
	return evaluation


def only_err(data_1, data_2):
	d_1 = {k:v for (k,v) in data_1.items() if v.failure is not None}
	return d_1, data_2



def main(arg):
	# Create the parser
	argparser = argparse.ArgumentParser(description='Visualizes correlation of two experiment steps.')

	# Add the arguments
	argparser.add_argument("-F", "--file", help="use specific input file", required=True)
	argparser.add_argument("-s", "--steps", help="name(s) of (two) urlgetter step(s) to investigate", required=True)
	argparser.add_argument("-e", "--onlyerrors", help="only consider failure cases", action="store_true")
	argparser.add_argument("-a", "--asn", help="asn")
	argparser.add_argument("-cl", "--classifier", help="the classifier to separate classes of measurements, e.g. step or probe_asn", required=True)
	argparser.add_argument("-c", "--sanitycheck", help="report file with sanity check measurement")
	out = argparser.parse_args()

	steps = out.steps.split(" ")

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

	evaluation = {}

	asns = []
	if out.asn is not None:
		asns = out.asn.split(",")
		
	files = [out.file]
	if os.path.isdir(out.file):
		files = glob.glob(out.file+"/*.json*")
		outpath = out.file
	else:
		outpath = os.path.dirname(out.file)

	filename = "result"
	for a in asns:
		filename += "_" + a
		break
	for s in steps:
		filename += "_" + s
	if out.sanitycheck:
		filename += "_checked"
		
	outpath = os.path.join(outpath, filename)


	print("Processing files...", files, "\n")

	possible_asns = {}
	inputs = {}
	collector = MeasurementCollector(out.classifier, steps)
	min_time_stamp = None
	max_time_stamp = None

	for f in files:
		if "_evaluation.json" in f:
			continue
		if "sanity" in f or "oldlist" in f:
			continue
		fileID = f.split("/")[-1]
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
		

			if data["test_name"] == "quicping":
				if data["input"] in unstable_hosts:
					continue
				mID = Measurement.mID(data, fileID, data["annotations"]["measurement_url"])
				msrmnt = QuicpingMeasurement(data, id)
			
			elif data["test_name"] == "urlgetter":
				if not "urlgetter_step" in data["annotations"]:
					continue
			
				step = data["annotations"]["urlgetter_step"]

				if not ("_inverse" in step):
					url_ = data["input"]
				if url_ in unstable_hosts:
					continue
			

				# mID = fileID + "-" + url_ + data["probe_asn"] + data["test_name"]
				mID = Measurement.mID(data, fileID, url_)
				msrmnt = URLGetterMeasurement(data, mID)

				if msrmnt.unexpectedly_ran_resolve():
					continue
			
				# disregard DNS failures
				if msrmnt.failed_op == "resolve":
					continue

			else:
				continue
			if msrmnt.step not in steps:
				continue
			if len(asns) > 0 and msrmnt.probe_asn not in asns:
				continue
			if "_sni" in msrmnt.step and msrmnt.failure is not None and ("ssl_failed_handshake" in msrmnt.failure or "tls: handshake failure" in msrmnt.failure):
				print("sni failure")
				continue

			if collector.has_id(mID, msrmnt):
				print("already in collector", mID, data["test_name"], data["measurement_start_time"])
				continue

			collector.add_by_ID(msrmnt)

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


	evaluation["test_list"] = inputs
	evaluation["test_list_length"] = len(inputs.keys())
	evaluation["asn"] = list(possible_asns.keys())
	evaluation["time_span"] = [min_time_stamp, max_time_stamp]

	

	for v,d in collector.class_items():
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

	
	# consistency(collector, steps, outpath)
	# sys.exit()


	dict_1, dict_2 = collector.classes()
	if out.onlyerrors:
		dict_1, dict_2 = only_err(dict_1, dict_2)

	evaluation = conditional_eval(dict_1, dict_2, evaluation)
	evaluation = sankey(steps, dict_1, dict_2, outpath, evaluation)


	with open(outpath +"_evaluation.json", "w") as e:
		json.dump(evaluation, e, indent=4, sort_keys=True, default=str)


		
if __name__ == "__main__":
	main(sys.argv[1:])