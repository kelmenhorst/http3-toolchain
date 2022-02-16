from urllib.parse import urlparse
import re

class Measurement:
	@staticmethod
	def mID(data, fileID, url):
		return fileID + "-" + url + data["probe_asn"] + data["test_name"]
		
	def __init__(self, data, id):
		self.data = data
		self.id = id
		self.tk = data["test_keys"]
		self.input_url = data["input"]
		self.input_domain = urlparse(self.input_url).netloc
		self.probe_asn = data["probe_asn"]
		self.probe_country = data["probe_cc"]
		self.test_name = data["test_name"]

class QuicpingMeasurement(Measurement):
	def __init__(self, data, id):
		Measurement.__init__(self, data, id) 
		self.domain = self.tk["domain"]
		self.pings = self.tk["pings"]

class URLGetterMeasurement(Measurement): 
	def __init__(self, data, id):
		Measurement.__init__(self, data, id) 
		self.failure = self.tk["failure"]
		self.ops = self.get_successful_operations()
		self.failed_op = self.get_failed_operation()
		self.proto = self.tk["requests"][0]["request"]["x_transport"]
		self.step = data["annotations"]["urlgetter_step"]
		try:
			self.probe_ip = self.tk["queries"][0]["answers"][0]["ipv4"]
		except:
			pass
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
	
	# when there is a redirect, another DNS resolve step is necessary
	# this resolve can be manipulated / censored
	def unexpectedly_ran_resolve(self):
		events = self.tk["network_events"]
		resolve = False
		for i, e in enumerate(events):
			if e["operation"] == "resolve_start":
				# when the cache is used, resolve_done should come immediately after resolve_start
				if events[i+1]["operation"] != "resolve_done":
					print("possible DNS manipulation", self.input_url)
					return True
		return False
	
	# get response server
	def get_server(self):
		try:
			headers = (self.tk["requests"][-1]["response"]["headers_list"])
			for h in headers:
				if h[0] == "Server":
					return h[1].lower()
		except KeyError as e:
			return None
		except TypeError as e:
			return None
	