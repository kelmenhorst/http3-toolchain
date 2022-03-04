from visualize import plt
from matplotlib import mlab
import numpy as np
import sys
import socket
import seaborn as sns
from matplotlib.ticker import FormatStrFormatter


def runtimes(dicts, stepnames, outpath, only_err=False):
    for i, n in enumerate(stepnames):
        stepnames[i] = n.replace("_cached", "")

    plotdata = []
    for i,data in enumerate(dicts.values()):
        cons = []
        for k, q in data.items():
            if q.failure is not None:
                continue
            cons.append(q.runtime)
        plotdata.append(cons)

    colors = ["r", "c"]
    fig = plt.figure()
    print(plotdata)
    xticks = []
    for i, pl in enumerate(plotdata):
        a = sns.kdeplot(data = pl, cumulative = True, label=stepnames[i], color=colors[i])
        avg = sum(pl)/len(pl)
        xticks.append(avg)
        plt.vlines(avg, 0, 1, colors=colors[i], linewidth=0.5)
    
    plt.ylabel("% of requests")
    plt.xticks(xticks + [3,5,7,9], rotation=45)
    plt.xlim(0, 5)
    plt.gca().xaxis.set_major_formatter(FormatStrFormatter('%.3g'))
    plt.legend()
    plt.xlabel("Runtime [s]")

    
    plt.savefig(outpath+"_runtimes.pdf")