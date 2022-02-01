import json
import sys
import os
import glob
from urllib.parse import urlparse
import matplotlib as mpl
mpl.rcParams['pdf.fonttype'] = 42
mpl.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib import cm
import argparse
import gzip
import sys
import pandas as pd
import re
from bokeh import io
import holoviews as hv
from holoviews import opts, dim
hv.extension('bokeh')
from datetime import datetime

SMALL_SIZE = 8
MEDIUM_SIZE = 10
BIGGER_SIZE = 12

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=SMALL_SIZE)     # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

CMAP = {
	"success":"powderblue",
	"success ":"powderblue",
	"TCP-hs-to": "lightcoral",
	"TCP-hs-to ": "lightcoral",
	"TCP-hs": "lightcoral",
	"TLS-hs-to": "firebrick",
	"TLS-hs-to ": "firebrick",
	"TLS-hs": "firebrick",
	"QUIC-hs-to": "coral",
	"QUIC-hs-to ": "coral",
	"handshake\ntimeout": "coral",
	"QUIC-hs": "coral",
	"conn-to": "peru",
	"conn-to ": "peru",
	"conn": "peru",
	"conn ": "peru",
	"EOF-err": "orangered",
	"conn-refused": "lightpink",
	"conn-reset": "crimson",
	"stopped after 10 redirects": "rosybrown",
	"proto-err": "rosybrown",
	"route-err": "rosybrown",
	"ssl-invalid-hostname": "rosybrown",
	"ssl-invalid-hostname ": "rosybrown",
	"Temporary failure in name resolution": "lightpink",
	"TLS-err": "tomato"
}

IGNORE_ERR = ["quic-incompatible-version", "http", "Read on stream 0 canceled with error code 268", "FRAME_ENCODING_ERROR"]
IGNORE_SMALLER_VALUES = 0

timestamp_fmt = '%Y-%m-%d %H:%M:%S'

class Measurement: 
	def __init__(self, data, id):
		self.data = data
		self.id = id
		self.tk = data["test_keys"]
		self.failure = self.tk["failure"]
		self.input_url = data["input"]
		self.input_domain = urlparse(self.input_url).netloc
		self.probe_asn = data["probe_asn"]
		self.probe_country = data["probe_cc"]
		self.ops = self.get_successful_operations()
		self.failed_op = self.get_failed_operation()
		self.proto = self.tk["requests"][0]["request"]["x_transport"]
		self.step = data["annotations"]["urlgetter_step"]
		self.probe_ip = self.tk["queries"][0]["answers"][0]["ipv4"]
		try:
			self.sni = self.tk["tls_handshakes"][0]["server_name"]
		except:
			self.sni = urlparse(self.input_url).netloc
			# for o in data["options"]:
			# 	if "TLSServerName" in o:
			# 		self.sni = o.split("=")[1]
		
	def error_type(self):
		# if self.closedconn():
		# 	self.failure = "Use of closed network connection"
		# 	return "conn-reset"
		r = re.compile('.*_handshake_done')
		if self.failure is None:
			return "success"
		if "connect: no route to host" in self.failure:
			return "route-err"
		elif self.failure == "generic_timeout_error":
			if r'.*_handshake_done' in self.ops:
				return "conn-to"
			else:
				return self.failed_op + "-to"
		elif "No recent network activity" in self.failure:
			if any(r.match(op) for op in self.ops):
				return "conn-to"
		elif "eof" in self.failure:
			return "EOF-err"
		elif "PROTOCOL_ERROR" in self.failure:
			return "proto-err"
		elif "unknown_failure" in self.failure:
			if "tls:" in self.failure:
				return "TLS-err"
			return self.failure.split(":")[-1].strip()
		return self.failure.replace("_", "-").replace("connection", "conn")

	def closedconn(self):
		t = False
		for e in self.tk["network_events"]:
			if e["failure"] and "use of closed network connection" in e["failure"]:
				t = True
		if t:
			return True
		else:
			return False

	def get_successful_operations(self):
		if self.tk["failed_operation"] is None:
			return None
		events = self.tk["network_events"]
		successful_operations = []
		for e in events:
			if e["failure"] is not None:
				break
			if successful_operations == [] or (successful_operations[-1] != e["operation"]):
				successful_operations.append(e["operation"])
		return successful_operations
	
	def get_failed_operation(self):
		op = self.tk["failed_operation"]
		if op == "connect":
			return "TCP-hs"
		elif op == "tls_handshake":
			return "TLS-hs"
		elif op == "quic_handshake":
			return "QUIC-hs"
		elif op == "top_level":
			return "conn"
		else:
			return op


def sankey(steps, data_1, data_2, outpath, evaluation):
	print("\n\n\nCorrelation Matrix (Sankey)\n")
	global cc
	global save_plot
	
	failures_1 = []
	failures_2 = []
	for k,t in data_1.items():
		if not k in data_2:
			continue
		if t.error_type() in IGNORE_ERR:
			continue
		e_t = t.error_type()
		q = data_2[k]
		if q.error_type() in IGNORE_ERR:
			continue
		e_q = q.error_type()+ " "
		failures_1.insert(0, e_t)
		failures_2.insert(0,e_q)
		
	n = len(failures_1)

	# create a df from the data
	df_links = pd.DataFrame([failures_1, failures_2], steps).T
	df_links = df_links.groupby(steps).apply(len)

	# convert the groupby into a dataframe
	df_links = df_links.to_frame().reset_index()

	# rename the 0 column with value
	df_links.rename(columns = {0:"value"}, inplace = True)
	df_links = df_links[df_links.value > IGNORE_SMALLER_VALUES]

	totals_t = {}
	totals_q = {}
	for index, row in df_links.iterrows():
		step_1 = row[steps[0]]
		v = totals_t.get(step_1,0)
		totals_t[step_1] = v + row.value
		step_2 = row[steps[1]]
		v = totals_q.get(step_2,0)
		totals_q[step_2] = v + row.value

	for index, row in df_links.iterrows():
		v = totals_t[row[steps[0]]]
		q = v*100/n
		if q < 0.5:
			df_links.at[index,steps[0]] = 'other'
		v = totals_q[row[steps[1]]]
		q = v*100/n
		if q < 0.5:
			df_links.at[index,steps[1]] = 'other '
	
	print(df_links)
	df_links = df_links.groupby(steps).agg({'value': 'sum'}).apply(lambda x: x*100/n)
	print(df_links)
	evaluation["matrix"] = df_links

	value_dim = hv.Dimension('value', unit='%', value_format=lambda x: '%.1f' % x)
	sankey = hv.Sankey(df_links, kdims=steps, vdims=value_dim)

	hv.extension('matplotlib')
	sankey.opts(opts.Sankey(cmap=CMAP,labels='index', edge_color=dim(steps[0]).str(),node_color=dim('index').str(), label_text_font_size="xx-large", label_position="outer", node_width=50, show_values=True, fig_size=160))
	# hv.output(sankey, fig='pdf', backend='matplotlib')
	hv.Store.renderers['matplotlib'].save(sankey, outpath, 'pdf')
	
	return evaluation
	

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
					qn = q_errors.get(data_q[id].error_type(),0)
					q_errors[data_q[id].error_type()] = qn + 1
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
			

			mID = fileID + "-" + url_ + data["probe_asn"]
			msrmnt = Measurement(data, mID)
			
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

	with open(outpath +"_evaluation.json", "w") as e:
		json.dump(evaluation, e, indent=4, sort_keys=True, default=str)


		
if __name__ == "__main__":
	main(sys.argv[1:])