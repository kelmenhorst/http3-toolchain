import matplotlib.pylab as plt
import numpy as np
from matplotlib.lines import Line2D
import sys
from dateutil import parser

# point in time number of bytes recv

datapoints_b = []
datapoints_t = []

def integr(x, y_array):
    sum = 0
    for b in range(x+1):
        sum += y_array[b]
    return sum

colors = {"quic_cached": "c", "tcp_cached":"r", "AS60178": "r", "AS58224": "c"}


# "The read_speed is defined as the number of bytes read divided by the time of the last successful operation.""
# From: https://ooni.org/post/2022-russia-blocks-amid-ru-ua-conflict/#twitter-throttled
def throttling_read_speed(collector):
    y_read_speeds = {}
    times = {}
    for step in collector:
        y_read_speeds[step] = []
        times[step] = []

    for step, measurement_data in reversed(collector.class_items()):
        for _, measurement in measurement_data.items():
            read_write_stats = measurement.read_write_stats()
            for rw in read_write_stats:
                if rw['time_to_last_read_ok'] > 0:
                    read_speed = float(rw['read_bytes'])/rw['time_to_last_read_ok']
                    y_read_speeds[step].append(read_speed)
                    times[step].append(measurement.measurement_start_time)
    
    for step in collector:
        ti = [parser.parse(t) for t in times[step]]
        plt.scatter(ti, y_read_speeds[step], color=colors[step], edgecolors='white')
    plt.ylim(-1000, 600000)
    plt.savefig("readspeed.pdf")



# collector is a dictionary of dictionaries
def throttling(collector, savepdf):
    urls_by_bytes = {}
    steps = {}

    for step, measurement_data in reversed(collector.class_items()):
        unique_urls = {}
        data = {}
        for id, measurement in measurement_data.items():
            if measurement.failure is not None:
                continue
            for s, alt in collector.class_items():
                if s == step:
                    continue
                if measurement.id not in alt or alt[measurement.id].failure is not None:
                    continue
            datapoints_t = []
            datapoints_b = []
            
            try:
                n_events = measurement.tk["network_events"]
                s = 0
                for e in n_events:
                    try:
                        if not "read" in e["operation"]:
                            continue
                        t = e["t"]
                        b = e["num_bytes"]
                        datapoints_t.append(t)
                        datapoints_b.append(b)
                        s += b       
                    except:
                        pass
                
                urls_by_bytes[s] = measurement.input
                unique_urls[measurement.input] = True 
                data[measurement.id] = {"u": measurement.input, "t": datapoints_t, "b": datapoints_b}

            except:
                pass

        steps[step] = (unique_urls, data)
    
    for step, (urls, data) in reversed(steps.items()):
        ct = 0
        for s, (other_urls,_) in steps.items():
            if s == step:
                continue

        for id, tuple in data.items():
            if not tuple["u"] in other_urls:
                continue
            ct += 1
            print(step)
            plt.plot(tuple["t"], [integr(t, tuple["b"]) for t in range(len(tuple["t"]))], color=colors[step], label=step, linewidth=0.5, alpha=0.5)
           
    print("biggest downloads:", sorted(urls_by_bytes.items(), reverse=True)[0:20])
    
    hndls = []
    for s in collector.classifiers():
        line = Line2D([0], [0], label=s, color=colors[s])
        hndls.append(line)

    plt.legend(handles=hndls)
    plt.xlabel("time[s]")
    plt.ylabel("bytes")
    title = plt.title("Resource loading")
    plt.xlim(0, 5)
    plt.ylim(bottom = -200, top=3000000)
    if savepdf:
        plt.savefig("throttling.pdf")
    else:
        plt.show()