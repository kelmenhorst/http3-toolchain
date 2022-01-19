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
			for o in data["options"]:
				if "TLSServerName" in o:
					self.sni = o.split("=")[1]
		
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


def sankey(steps, data_1, data_2):
	print("\n\n\nCorrelation Matrix (Sankey)\n")
	global cc
	global save_plot
	
	failures_1 = []
	failures_2 = []
	for k,t in data_1.items():
		if not k in data_2:
			continue
		e = t.error_type()
		q = data_2[k]
		failures_1.insert(0, e)
		e = q.error_type()+ " "
		failures_2.insert(0,e)
		
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
		if q < 1:
			df_links.at[index,steps[0]] = 'other'
		v = totals_q[row[steps[1]]]
		q = v*100/n
		if q < 1:
			df_links.at[index,steps[1]] = 'other '
	
	print(df_links)
	df_links = df_links.groupby(steps).agg({'value': 'sum'}).apply(lambda x: x*100/n)
	print(df_links)

	value_dim = hv.Dimension('value', unit='%', value_format=lambda x: '%.1f' % x)
	sankey = hv.Sankey(df_links, kdims=steps, vdims=value_dim)

	hv.extension('matplotlib')
	sankey.opts(opts.Sankey(cmap=CMAP,labels='index', edge_color=dim(steps[0]).str(),node_color=dim('index').str(), label_text_font_size="xx-large", label_position="outer", node_width=50, show_values=True, fig_size=160))
	# hv.output(sankey, fig='pdf', backend='matplotlib')
	hv.Store.renderers['matplotlib'].save(sankey, "flows", 'pdf')
	

def tcpblocked_cli(data_t, data_q, keyword=None):
	print(type(data_q))
	failures = [v.error_type() for (k,v) in data_t.items() if v.failure is not None]
	u_failures = list(dict.fromkeys(failures))

	for f in u_failures:
		q_errors = {}
		print("\n"+f, failures.count(f))
		for id, d in data_t.items():
			if d.error_type() == f:
				try:
					print("---", data_q[id].error_type(), data_t[id].failed_op, data_q[id].failed_op)
					qn = q_errors.get(data_q[id].error_type(),0)
					q_errors[data_q[id].error_type()] = qn + 1
				except KeyError as e:
					pass


def main(arg):
	# Create the parser
	argparser = argparse.ArgumentParser(description='List the content of a folder')

	# Add the arguments
	argparser.add_argument("-e", "--experiment", help="experiment name, default: urlgetter")
	argparser.add_argument("-m", "--method", help="eval method")
	argparser.add_argument("-sk", "--skiphandshake", help="skip filtering handshake timeout errors",action='store_true', default=False)
	argparser.add_argument("-F", "--file", help="use specific input file")
	argparser.add_argument("-S", "--save", help="save plot")
	argparser.add_argument("-s", "--steps", help="name(s) of (two) urlgetter step(s) to investigate", required=True)
	out = argparser.parse_args()

	steps = out.steps.split(" ")

	experiment = out.experiment
	if experiment is None:
		experiment = "urlgetter"
	
	global mm 
	mm = out.method
	global save_plot 
	save_plot = None
	
	if out.save:
		size = out.save.split(" ")
		if len(size) == 1:
			save_plot = (float(size[0]),float(size[0])*2/3)
		elif len(size) == 2:
			save_plot = (float(size[0]), float(size[1]))
		print(save_plot)
		
	files = [out.file]
	if os.path.isdir(out.file):
		files = glob.glob(out.file+"/*.json*")
	print("Processing files...", files, "\n")


	inputs = []
	dicts = {}
	for step in steps:
		dicts[step] = {}

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
			print(data["test_keys"]["endpoints"][0]["tcp_connect"])
			sys.exit()
			if not "urlgetter_step" in data["annotations"]:
				continue
			
			
			try:
				probed_ip = data["test_keys"]["queries"][0]["answers"][0]["ipv4"]
			except:
				# print(data["input"], data["annotations"]["urlgetter_step"])
				continue
			url_ = data["input"]
			if url_ not in inputs:
				inputs.append(url_)
			
			step = data["annotations"]["urlgetter_step"]
			step = step.split("_",1)
			if len(step) > 1:
				method = step[1]
			else:
				method = ""

			mID = fileID + "-" + url_	
			msrmnt = Measurement(data, mID)
			try:
				while mID in dicts[msrmnt.step]:
					print("already in dict", mID)
					mID += "(1)"
				dicts[msrmnt.step][mID] = msrmnt
			except:
				pass

	for v,d in dicts.items():
		frate = {k:v for (k,v) in d.items() if v.failure is not None}
		print("failures in step", v+":", len(frate), "/", len(d))
		failures = [v.error_type() for v in frate.values()]
		u_failures = list(dict.fromkeys(failures))

		for f in u_failures:
			q_errors = {}
			print("--",f, failures.count(f))

	if len(steps) == 1:
		sys.exit()

	tcpblocked_cli(*dicts.values())
	sankey(steps, *dicts.values())

		
if __name__ == "__main__":
	main(sys.argv[1:])