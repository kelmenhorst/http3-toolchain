import matplotlib as mpl
mpl.rcParams['pdf.fonttype'] = 42
mpl.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt

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
	"ping-to": "orangered",
	"ping-to ": "orangered",
	"conn-refused": "lightpink",
	"conn-refused ": "lightpink",
	"conn-reset": "crimson",
	"conn-reset ": "crimson",
	"stopped after 10 redirects": "rosybrown",
	"proto-err": "rosybrown",
	"route-err": "rosybrown",
	"ssl-invalid-hostname": "rosybrown",
	"ssl-invalid-hostname ": "rosybrown",
	"Temporary failure in name resolution": "lightpink",
	"TLS-err": "tomato"
}