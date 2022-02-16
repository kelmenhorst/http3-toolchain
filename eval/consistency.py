from visualize import plt
import numpy as np

def consistency(_data_1, _data_2, only_err=False):
	# s = ['https://doordash.com', 'https://thehindu.com', 'https://tandfonline.com', 'https://mdpi.com', 'https://pars.host/']
	data_1 = {k:v for (k,v) in _data_1.items() if  not ("dnscache_example" in k or "dnscache_cloudflare" in k or "dnscache_target" in k or "dnscache_" in k)}
	data_2 = {k:v for (k,v) in _data_2.items() if not ("dnscache_example" in k or "dnscache_cloudflare" in k or "dnscache_target" in k)}

	plotdata = []
	for i,data in enumerate([data_1, data_2]):
		host_map = {}
		for k, q in data.items():
			host = q.input_url.replace("https://", "")
			e = q.error_type()
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
		print((host_map))
		for host, events in host_map.items():
			max_e = max(events, key=events.get)
			s = sum(events.values())
			q = [v/s for v in events.values()]
			max_quotient = max(q)
			if max_quotient < 1 and host not in out:
				out.append(host)
			cons.append(max_quotient*100)
		print(len(cons))
		plotdata.append(cons)
		print("O",cons)

	fig = plt.figure()
	
	fig.set_size_inches((3.77, 2.12))
	outliers = [[],[]]
	ct = 0

	for i, a in enumerate(plotdata[0]):
		b = plotdata[1][i]
		if not (a == 100):
			outliers[0].append(a)
		if not (b == 100):
			outliers[1].append(b)
			
		else:
			ct += 1
	
	plt.plot(outliers[0], linestyle='none', marker='|', color="powderblue", markersize=7, mew=2)
	plt.plot(outliers[1], linestyle='none', marker='.', color="lightcoral", alpha=0.5, markersize=6, mew=1.5)
	
	# plt.ylim(0, 105)
	# plt.xlim(left=-1)
	plt.xticks(np.arange(0, len(outliers[0]),1))
	# plt.ylim(bottom=61)
	plt.xlabel("Domain IDs \n*cleaned from domains with result consistency = 100%")
	plt.legend(["QUIC", "TCP/TLS"])
	plt.ylabel("Result consistency [%]")
	plt.tight_layout()
	
	
	# plt.savefig("../plots/"+cc+"_"+dd+"_consistency_qerr2.pdf")
	plt.show()

	hx, hy, _ = plt.hist(plotdata[0],bins=20,histtype='step',cumulative=True, density=True)
	hx_t, hy_t, _ = plt.hist(plotdata[1],bins=20,histtype='step',cumulative=True, density=True)
	plt.close()
	print(hx, hy)
	print(hx_t, hy_t)
	fig = plt.figure()
	fig.set_size_inches((2, 1.7))
	pdf = hx / sum(hx)
	cdf = np.cumsum(pdf)*100
	plt.plot(hy[1:], cdf, label="CDF", color="powderblue")
	pdf = hx_t / sum(hx_t)
	cdf = np.cumsum(pdf)*100
	plt.plot(hy_t[1:], cdf, label="CDF", color="lightcoral")
	plt.ylabel("% of hosts")
	plt.yticks([20,40,60,80])
	plt.xticks([70,80,90,100])
	plt.legend(["QUIC", "TCP/TLS"])
	plt.xlabel("Result consistency [%]")
	plt.ylim(0,100)
	plt.tight_layout()
	# plt.title("Empirical CDF")

	
	# plt.savefig("../plots/"+cc+"_"+dd+"_consistency_cdf.pdf")
	plt.show()