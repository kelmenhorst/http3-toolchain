from visualize import plt, RAINBOW
from matplotlib import mlab
import numpy as np
import sys
import socket
import seaborn as sns
import numbers
from matplotlib.ticker import FormatStrFormatter


def runtimes(collector, outfile):
    stepnames = collector.classifiers()
    for i, n in enumerate(stepnames):
        stepnames[i] = n.replace("_cached", "")

    plotdata = []
    for data in collector.class_values():
        cons = []
        for k, q in data.items():
            if q.failure is not None:
                continue
            if isinstance(q.test_runtime, numbers.Number):
                cons.append(q.test_runtime)
        plotdata.append(cons)

    fig = plt.figure()
    xticks = []
    for i, pl in enumerate(plotdata):
        a = sns.kdeplot(data = pl, cumulative = True, label=stepnames[i], color=RAINBOW[i])
        avg = sum(pl)/len(pl)
        xticks.append(avg)
        plt.vlines(avg, 0, 1, colors=RAINBOW[i], linewidth=0.5)
    
    plt.ylabel("% of requests")
    plt.xticks(xticks + [3,5,7,9], rotation=45)
    plt.xlim(0, 5)
    plt.gca().xaxis.set_major_formatter(FormatStrFormatter('%.3g'))
    plt.legend()
    plt.xlabel("Runtime [s]")

    if outfile:
        plt.savefig(outfile)
    else:
        plt.show()