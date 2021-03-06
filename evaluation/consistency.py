from visualize import plt
import numpy as np
import sys
import socket
import json

def consistency(collector, outfile):
	stepnames = collector.classifiers()

	for i, n in enumerate(stepnames):
		try:
			stepnames[i] = list(json.loads(stepnames[i]).values())[0]
		except Exception as e:
			pass # ignore if this fails

	plotdata = []
	quic_failure_hosts = {}
	for i, data in enumerate(collector.class_values()):
		host_map = {}
		for k, q in data.items():
			host = q.input.replace("https://", "")
			e = q.error_type()
			if e != "success":
				quic_failure_hosts[host] = True
			host = host.split("/")[0]
			if host in host_map:
				if e in host_map[host]:
					host_map[host][e] += 1
				else:
					host_map[host][e] = 1

			else:
				host_map[host] = {}
				host_map[host][e] = 1

		cons = []
		out = []
		for host, events in host_map.items():
			max_e = max(events, key=events.get)
			s = sum(events.values())
			q = [v/s for v in events.values()]
			max_quotient = max(q)
			if max_quotient < 1 and host not in out:
				out.append(host)
			cons.append(max_quotient*100)
		plotdata.append(cons)


	fig = plt.figure()
	for pl in plotdata:
		hx, hy = np.histogram(pl,bins=20, density=True)
		hx = np.cumsum(hx)
		print(hx, hy)
		pdf = hx / sum(hx)
		cdf = np.cumsum(pdf)*100
		plt.plot(hy[1:], cdf, label="CDF")
	plt.ylabel("% of hosts")
	plt.yticks([20,40,60,80])
	plt.xticks([50,60,70,80,90,100])
	plt.legend(stepnames)
	plt.xlabel("Result consistency [%]")
	plt.ylim(0,100)
	plt.tight_layout()

	fig.set_size_inches((3, 2.3))
	plt.tight_layout()
	if outfile:
		plt.savefig(outfile)
	else:
		plt.show()