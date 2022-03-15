from urllib.parse import urlparse
import re

class Measurement:
	@staticmethod
	def mID(data, fileID, i):
		return fileID + "-" + data["probe_asn"] + "--" + i 
		
	def __init__(self, data, id):
		self.data = data
		self.id = id
		self.tk = data["test_keys"]
		self.probe_asn = data["probe_asn"]
		self.probe_country = data["probe_cc"]
		self.test_name = data["test_name"]
		self.time = data["measurement_start_time"]
		self.runtime = data["test_runtime"]

class QuicpingMeasurement(Measurement):
	def __init__(self, data, id):
		Measurement.__init__(self, data, id) 
		self.input_url = data["annotations"]["measurement_url"]
		self.input_domain = urlparse(self.input_url).netloc
		self.domain = self.tk["domain"]
		self.pings = self.tk["pings"]
		self.step = "quicping"
		self.failure = None
		self.proto = "quicping"
		try:
			self.runtime = self.pings[0]["responses"][0]["t"] - 1
		except:
			self.runtime = ""
			pass
		pingresults = [p["failure"] for p in self.pings]
		if None in pingresults:
			self.failure = None
		else:
			self.failure = pingresults[0]
		self.failed_op = None
		if self.failure is not None:
			self.failed_op = "ping"
		self.probe_ip = data["input"]
	
	def get_server(self):
		return None


	def error_type(self):
		if self.failure is None:
			return "success"
		if "connect: no route to host" in self.failure:
			return "route-err"
		elif self.failure == "generic_timeout_error":
			return "ping-to"
		elif "unknown_failure" in self.failure:
			if "tls:" in self.failure:
				return "TLS-err"
			return self.failure.split(":")[-1].strip()
		return self.failure.replace("_", "-").replace("connection", "conn")


class URLGetterMeasurement(Measurement): 
	def __init__(self, data, id):
		Measurement.__init__(self, data, id) 
		self.input_url = data["input"]
		self.input_domain = urlparse(self.input_url).netloc
		self.failure = self.tk["failure"]
		self.ops = self.get_successful_operations()
		self.failed_op = self.get_failed_operation()
		self.step = data["annotations"]["urlgetter_step"]
		try:
			self.probe_ip = self.tk["queries"][0]["answers"][0]["ipv4"]
		except:
			self.probe_ip = ""
			pass
		try:
			self.proto = self.tk["requests"][0]["request"]["x_transport"]
		except: # assume this flag is set correctly
			if "HTTP3Enabled=true" in data["options"]:
				self.proto = "quic"
			else:
				self.proto = "tcp"
		try:
			self.sni = self.tk["tls_handshakes"][0]["server_name"]
		except:
			self.sni = urlparse(self.input_url).netloc
		
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
		if events is None:
			return None
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

	def read_write_stats(self):
		if 'network_events' not in self.tk:
			return None

		address = None
		t0 = None
		tls_handshake_started = False
		stats = {
			'read_count': 0,
			'write_count': 0,
			'read_bytes': 0,
			'write_bytes': 0,
			'time_to_last_read': 0,
			'time_to_last_write': 0,
			'time_to_last_read_ok': 0,
			'time_to_last_write_ok': 0,
		}
		tls_handshakes = []
		for ne in self.tk['network_events']:
			if ne['operation'] == 'connect':
				address = ne['address']
				tls_handshake_started = False
				t0 = ne['t']
				stats = {
					'read_count': 0,
					'write_count': 0,
					'read_bytes': 0,
					'write_bytes': 0,
					'time_to_last_read': 0,
					'time_to_last_write': 0,
					'time_to_last_read_ok': 0,
					'time_to_last_write_ok': 0,
					'last_failure_read': None,
					'last_failure_write': None,
					'last_failure': None
				}
			
			if ne['operation'] == 'tls_handshake_start':
				tls_handshake_started = True

			if ne['operation'] == 'quic_handshake_start':
				tls_handshake_started = True
				t0 = ne['t']
				stats = {
					'read_count': 0,
					'write_count': 0,
					'read_bytes': 0,
					'write_bytes': 0,
					'time_to_last_read': 0,
					'time_to_last_write': 0,
					'time_to_last_read_ok': 0,
					'time_to_last_write_ok': 0,
					'last_failure_read': None,
					'last_failure_write': None,
					'last_failure': None
				}
			
			if '_handshake_done' in ne['operation']:
				stats.update({'address': address})
				tls_handshakes.append(stats)
				tls_handshake_started = False
			
			# if not tls_handshake_started:
			# 	continue
			
			if 'read' in ne['operation']:
				stats['read_count'] += 1
				stats['read_bytes'] += ne.get('num_bytes', 0)
				stats['time_to_last_read'] = ne['t'] - t0
				if not ne['failure']:
					stats['time_to_last_read_ok'] = ne['t'] - t0
				else:
					stats['last_failure_read'] = ne['failure']
				
			if 'write' in ne['operation']:
				if "address" in ne:
					address = ne["address"]
				stats['write_count'] += 1
				stats['write_bytes'] += ne.get('num_bytes', 0)
				stats['time_to_last_write'] = ne['t'] - t0
				if not ne['failure']:
					stats['time_to_last_write_ok'] = ne['t'] - t0
				else:
					stats['last_failure_write'] = ne['failure']

		if tls_handshake_started:
			stats.update({'address': address})
			tls_handshakes.append(stats)
		return tls_handshakes


	def network_wait_time(self):
		j = 0
		last = None
		for i, n in enumerate(self.tk["network_events"]):
			# during wait time
			if "write" in n["operation"] and last is not None:
				continue
			if "write" in n["operation"]:
				last = n["t"]
			if "read" in n["operation"] and last is not None:
				j += n["t"] - last
				last = None
		return j