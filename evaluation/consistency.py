from visualize import plt
import numpy as np

def consistency(_data_1, _data_2, stepnames, outpath, only_err=False):
	# s = ['https://doordash.com', 'https://thehindu.com', 'https://tandfonline.com', 'https://mdpi.com', 'https://pars.host/']
	data_1 = {k:v for (k,v) in _data_1.items()}
	data_2 = {k:v for (k,v) in _data_2.items()}

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
	plt.legend([stepnames[0], stepnames[1]])
	plt.xlabel("Result consistency [%]")
	plt.ylim(0,100)
	plt.tight_layout()
	# plt.title("Empirical CDF")

	
	plt.savefig(outpath+"_consistency.pdf")
	# plt.show()