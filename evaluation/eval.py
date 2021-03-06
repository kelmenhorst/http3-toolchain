import json
import sys
import os
import glob
import argparse
import gzip
from datetime import datetime

from measurement import Measurement, URLGetterMeasurement, QuicpingMeasurement

verbose = False


class MeasurementCollector:
	def __init__(self, classes):
		self.classes = classes
		self.collection = {}
		for c in self.classes:
			key = json.dumps(c)
			self.collection[key] = {}
	
	def check_and_add(self, measurement):
		cl = self.check(measurement)
		if cl is None:
			return

		key = json.dumps(cl)
		if measurement.id in self.collection[key]:
			if verbose:
				print("already in collector", key, measurement.id)
			return
		self.collection[key][measurement.id] = measurement

	def check(self, measurement):
		belongs_to = None
		for clss in self.classes:
			belong_to_class = True
			for k, v in clss.items():
				try:
					measurement_attr = getattr(measurement, k)
					if type(v) == list:
						if measurement_attr not in v:
							belong_to_class = False
						continue
					if k == "failure" and v == "*":
						if measurement_attr is None:
							belong_to_class = False
						continue
					if v != measurement_attr:
						belong_to_class = False
				except AttributeError as e:
					if verbose:
						print(e)
					belong_to_class = False
			if belong_to_class:
				return clss
		return None

	def class_items(self):
		return self.collection.items()

	def class_values(self):
		return self.collection.values()
	
	def classifiers(self):
		return list(self.collection.keys())


def conditional_eval(collector, evaluation):
	data_1, data_2 = collector.class_values()

	failures = [v.error_type() for (k,v) in data_1.items() if v.failure is not None]
	u_failures = list(dict.fromkeys(failures))

	evaluation["conditional_eval"] = {}

	for f in u_failures:
		q_errors = {}
		print("\n"+f, failures.count(f))
		evaluation["conditional_eval"][f] = {}
		evaluation["conditional_eval"][f]["n"] = failures.count(f)

		for id, d in data_1.items():
			if d.error_type() == f:
				try:
					print("---", data_2[id].error_type(), data_1[id].failed_op, data_2[id].failed_op)
					qn = q_errors.get(data_2[id].error_type(),[])
					qn.append(data_2[id].input+" "+data_2[id].probe_ip)
					q_errors[data_2[id].error_type()] = qn
					
				except KeyError as e:
					pass
		
		evaluation["conditional_eval"][f]["step_2"] = q_errors
	return evaluation

def print_urls(collector, outfile):
	for k, clss in collector.class_items():
		urls = {}
		print("\n"+k+"\n")
		for measurement in clss.values():
			if measurement.input in urls:
				urls[measurement.input] += 1
			else:
				urls[measurement.input] = 1
		print(urls)

def print_details(collector, outfile):
	for k, clss in collector.class_items():
		print("\n"+k+"\n")
		for measurement in clss.values():
			print(measurement.input, measurement.proto, measurement.failure, measurement.measurement_start_time, measurement.test_runtime)
			try:
				print("Sucessful operations:", measurement.get_successful_operations())
				stats = measurement.read_write_stats()
				print("Read bytes:", stats[0]["read_bytes"], "Read count:", stats[0]["read_count"])
			except:
				pass
			print(" ")

def eval(file, method, collector, sanitycheck, outfile):
	# output file
	if outfile:
		if not outfile.endswith(".pdf"):
			outfile += ".pdf"

	# sanity check
	unstable_hosts = {}
	if sanitycheck:
		lines = []
		with open(sanitycheck, "r") as scheck:
			lines = scheck.readlines()
		for l in lines:
			data = json.loads(l)
			if data["test_name"] == "quicping":
				continue
			if data["test_keys"]["failure"] is not None and not ("cloudflare" in data["input"] or "quic.nginx.org" in data["input"] or "plus.im" in data["input"]):
				unstable_hosts[data["input"]] = True
	print("\nUnstable hosts:", list(unstable_hosts.keys()))

	# evaluation stats
	evaluation = {}
	possible_asns = {}
	inputs = {}
	min_time_stamp = None
	max_time_stamp = None
	
	# input files
	files = [file]
	if os.path.isdir(file):
		files = glob.glob(file+"/*.json*")
	print("Processing files...", files, "\n")


	for f in files:
		if "_evaluation.json" in f:
			continue
		if "sanity" in f or "oldlist" in f or ".old" in f:
			continue
		fileID = f.split("/")[-1]
		if verbose:
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
				if data["annotations"]["measurement_url"] in unstable_hosts:
					continue
				mID = Measurement.mID(data, fileID, data["annotations"]["measurement_url"]+"_"+data["input"])
				msrmnt = QuicpingMeasurement(data, mID)
			
			elif data["test_name"] == "urlgetter":
				if not "urlgetter_step" in data["annotations"]:
					continue
			
				step = data["annotations"]["urlgetter_step"]

				if not ("_inverse" in step):
					url_ = data["input"]
				if url_ in unstable_hosts:
					continue
					
				try:
					probe_ip = data["test_keys"]["queries"][0]["answers"][0]["ipv4"]
				except:
					probe_ip = ""
					pass
				# create Measurement instance
				mID = Measurement.mID(data, fileID, url_+ "_" + probe_ip)
				msrmnt = URLGetterMeasurement(data, mID)

				# disregard DNS censorship
				if msrmnt.unexpectedly_ran_resolve():
					if verbose:
						print("possible DNS manipulation", msrmnt.input, msrmnt.failure)
					continue
			
				# disregard DNS failures
				if msrmnt.failed_op == "resolve":
					continue

			else:
				continue
			
			if msrmnt.test_name == "urlgetter" and "_sni" in msrmnt.urlgetter_step and msrmnt.failure is not None and ("ssl_failed_handshake" in msrmnt.failure or "tls: handshake failure" in msrmnt.failure):
				if verbose:
					print("sni failure", msrmnt.id)
				continue

			collector.check_and_add(msrmnt)

			# evaluation stats
			tstamp = datetime.strptime(data["measurement_start_time"], '%Y-%m-%d %H:%M:%S')
			if max_time_stamp is None or tstamp > max_time_stamp:
				max_time_stamp = tstamp
			if min_time_stamp is None or tstamp < min_time_stamp:
				min_time_stamp = tstamp
			if url_ not in inputs:
				inputs[url_] = [fileID]
			else:
				if fileID in inputs[url_]:
					continue
				inputs[url_].append(fileID)


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

	
	if method == "sankey":
		from sankey import sankey
		evaluation = conditional_eval(collector, evaluation)
		evaluation = sankey(collector, evaluation, outfile)
		if outfile:
			with open(outfile.replace(".pdf", "_evaluation.json"), "w") as e:
				json.dump(evaluation, e, indent=4, sort_keys=True, default=str)
	
	elif method == "throttling":
		from throttling import throttling
		throttling(collector, outfile)
	
	elif method == "consistency":
		from consistency import consistency
		consistency(collector, outfile)

	elif method == "runtimes":
		from runtimes import runtimes
		runtimes(collector, outfile)
	
	elif method == "print-details":
		print_details(collector, outfile)

	elif method == "print-urls":
		print_urls(collector, outfile)



		
if __name__ == "__main__":
	# Create the parser
	argparser = argparse.ArgumentParser(description='Visualizes correlation of two experiment steps.')

	# Add the arguments
	argparser.add_argument("-f", "--file", help="input file or folder", required=True)
	argparser.add_argument("-c", "--sanitycheck", help="report file with sanity check measurement")
	argparser.add_argument("-o", "--out", help="save result as pdf")
	argparser.add_argument("-v", "--verbose", action='store_true')
	argparser.add_argument("-S", "--sankey", help="sides of sankey diagram, json style object, (see ./examples, full list of possible attributes in README)")
	argparser.add_argument("-C", "--filters", help="file with classes to analyse, as filters, json style, (see examples, full list of possible attributes in README)")
	args, method = argparser.parse_known_args()

	verbose = args.verbose

	if not os.path.exists(args.file):
		print("Failure:", args.file, "doesn't exist. Exiting...")
		sys.exit()

	if args.filters:
		try:
			with open(args.filters, "r") as cf:
				data = cf.read()
			classes = json.loads(data)
			print("classes:", classes)
		except Exception as e:
			print("Failure: Parsing", args.filters, "failed:", e, ". Exiting...")
			sys.exit()
	
	if args.sankey:
		try:
			with open(args.sankey, "r") as cf:
				data = cf.read()
			filters = json.loads(data)
			left_filter = filters["left"]
			print("Sankey filter left:", left_filter)
			right_filter = filters["right"]
			print("Sankey filter right:", right_filter)

		except Exception as e:
			print("Failure: Parsing", args.sankey, "failed:", e, ". Exiting...")
			sys.exit()
		
	if len(method) != 1:
		print("Failure: Could not parse method. Exiting...")
		sys.exit()
	method = method[0]
	
	if method == "sankey" and left_filter and right_filter:
		collector = MeasurementCollector([left_filter, right_filter])
	elif method == "throttling" and classes:
		collector = MeasurementCollector(classes)
	elif method == "consistency" and classes:
		collector = MeasurementCollector(classes)
	elif method == "runtimes" and classes:
		collector = MeasurementCollector(classes)
	elif method == "print-urls" and classes:
		collector = MeasurementCollector(classes)
	elif method == "print-details" and classes:
		collector = MeasurementCollector(classes)
	else:
		print("Failure: Invalid configuration. Exiting...")
		sys.exit()

	eval(args.file, method, collector, args.sanitycheck, args.out)