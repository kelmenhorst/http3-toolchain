from eval import eval,  MeasurementCollector
import re
import sys
import os
import argparse
import time
import datetime
import gzip
import pandas

# get_asns returns the numbers of AS with HTTP/3 measurements in a specific country
def get_asns(cc, dates):
	# download csv file from github
	url = "https://raw.githubusercontent.com/kelmenhorst/http3-toolchain/master/measurement_list.csv"
	df = pandas.read_csv(url)	
	
	cc = cc.upper()
	df = df.loc[df["country"] == cc]
	asns = {}

	# iterate csv file and look for dates that fit the time frame
	for index, row in df.iterrows():
		if dates:
			measurement_date_str = row["date"]
			measurement_date = datetime.datetime.strptime(measurement_date_str, "%Y-%m-%d")
			if measurement_date < dates[0] or measurement_date > dates[1]:
				continue

		asn = row["asn"]
		asns[asn] = True
	
	return list(asns.keys())

# get_http3_measurements downloads measurement data in a certain AS and time frame into a folder named msrmnts
def get_http3_measurements(dates, asn):
	msrmnts_folder = "msrmnts"
	if not os.path.exists(msrmnts_folder):
		os.mkdir(msrmnts_folder)

	# download csv file from github
	url = "https://raw.githubusercontent.com/kelmenhorst/http3-toolchain/master/measurement_list.csv"
	df = pandas.read_csv(url)

	df = df.loc[df["asn"] == asn]

	# iterate csv file and look for dates that fit the time frame
	downloaded = 0
	for index, row in df.iterrows():
		measurement_date_str = row["date"]
		measurement_date = datetime.datetime.strptime(measurement_date_str, "%Y-%m-%d")

		if measurement_date < dates[0] or measurement_date > dates[1]:
			continue
		measurement_url = row["url"]
		filepath = os.path.join(msrmnts_folder, row["filename"])

		# download these file using the url field --> folder tmp
		cmd = "aws s3 --no-sign-request cp" + " " + measurement_url+ " " + filepath
		os.system(cmd)
		downloaded += 1

	if downloaded == 0:
		print("No matching measurement files. Exiting..")
		sys.exit()

	return msrmnts_folder


if __name__ == "__main__":
	# Create the parser
	argparser = argparse.ArgumentParser(description='Downloads, evaluates and visualizes HTTP/3 measurements taken with OONI\'s urlgetter experiment.')

	# Add the arguments
	argparser.add_argument("-f", "--file", help="input file or folder")
	argparser.add_argument("-a", "--asn", help="ASN to investigate, e.g. AS45090. You can also use a country code here to get a list of all ASNs with available HTTP/3 measurements in this country", required=True)
	argparser.add_argument("-d", "--dates", help="dates range to investigate, e.g. \"2022-02-01 2022-03-01\" ")
	argparser.add_argument("-o", "--out", help="save resulting plot as pdf, specify output file name here")
	args = argparser.parse_args()

	if re.match("^[A-Za-z]{2}$", args.asn):
		dates = None
		if args.dates:
			try:
				s, e = args.dates.split(" ")
				start = datetime.datetime.strptime(s, "%Y-%m-%d")
				end = datetime.datetime.strptime(e, "%Y-%m-%d")
				if start > end:
					print("Invalid input: Start date is later than end date.")
					sys.exit()
				dates = [start, end]
			except:
				print("Invalid input: date range format: \"yyyy-mm-dd yyyy-mm-dd\"")
				sys.exit()
		asns = get_asns(args.asn, dates)
		printstring = "Country " + args.asn + ": AS numbers"
		if args.dates:
			printstring += " in the time frame " + args.dates
		print(printstring)
		for a in asns:
			print(a)
		sys.exit()


	if not re.match("(AS|as)[0-9]+$", args.asn):
		print("Failure:", args.asn, "is not a valid ASN or country code")
		sys.exit()
	asn = args.asn.upper()

	if not args.file and not args.dates:
		print("Invalid input: Please specify either file (-f) or time frame (-d).")
		sys.exit()
	
	elif args.file:
		if args.dates:
			print("Warning: Ignore time frame and use input file.")
		if not os.path.exists(args.file):
			print("Failure:", args.file, "doesn't exist. Exiting...")
			sys.exit()
		files = args.file

	elif args.dates:
		try:
			s, e = args.dates.split(" ")
			start = datetime.datetime.strptime(s, "%Y-%m-%d")
			end = datetime.datetime.strptime(e, "%Y-%m-%d")
			if start > end:
				print("Invalid input: Start date is later than end date.")
				sys.exit()
		except:
			print("Invalid input: date range format: \"yyyy-mm-dd yyyy-mm-dd\"")
			sys.exit()
		print("Warning: This will download measurement files from OONI services using aws s3. You have 5 seconds to stop this process.")
		time.sleep(5)
		files = get_http3_measurements([start, end], asn)
	
	else:
		print("Invalid input: Please specify either file (-f) or time frame (-d).")
		sys.exit()

	left_filter = {
		"proto": "tcp",
		"urlgetter_step":["tcp_cached", "tcp_dnscache"],
		"probe_asn": asn
	}
	right_filter = {
		"proto": "quic",
		"urlgetter_step":["quic_cached", "quic_dnscache"],
		"probe_asn": asn
	}
	
	method = "sankey"
	collector = MeasurementCollector([left_filter, right_filter])

	# call eval to generate a Sankey diagram
	eval(files, method, collector, None, args.out)

