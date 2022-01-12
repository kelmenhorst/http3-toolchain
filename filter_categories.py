#!/usr/bin/env python3
import pandas
import sys
import urllib.request
import os
import argparse

# Filter out risky content categories: "XED", "GAYL", "PORN", "PROV", "DATE", "MINF", "REL", "LGBT"
# Input:  path_to_local_citizenlab input_txt_file

with urllib.request.urlopen("https://raw.githubusercontent.com/kush789/How-India-Censors-The-Web-Data/master/potentially_blocked_unique_hostnames.txt") as url:
			cis_india = (url.read().decode().splitlines())

def run(input_urls_filepath, local_filepath, global_filepath, target_dir):
	if global_filepath:
		df_global = pandas.read_csv(global_filepath, header=None, usecols=[0, 1])
	df_cc = pandas.read_csv(local_filepath, header=None, usecols=[0, 1])
	df = df_cc
	if global_filepath:
		df = pandas.concat([df_global], ignore_index=True)

	not_found = []
	ok = []
	with open(input_urls_filepath, "r") as urlsfile:
		for url in urlsfile:
			url = url.rstrip()
			ok.append(url)
			if url.endswith("/"):
				url = url[:-1]
			url = url.replace("https://", "")
			index = df[df[0].str.contains(r'.*'+url+'.*')].index.tolist()
			if not len(index):
				if "google" in url:
					continue
				if r'.*'+url+'.*' in cis_india:
					continue
				print("not found: ", url)
				not_found.append(url)
				ok = ok[:-1]
				continue
			category = ( df[1][index[0]])
			print(category)
			# remove websites from these categories
			if category in ["XED", "GAYL", "PORN", "PROV", "DATE", "MINF", "HUMR" "REL", "LGBT"] or "spankbang" in url:
				ok = ok[:-1]

	# Print urls that have not been found in source files.
	for l in not_found:
		print(l)

	out_file = os.path.join(target_dir, os.path.basename(input_urls_filepath)+".filtered.txt")
	with open(out_file, "w") as filteredfile:
		for item in ok:
			filteredfile.write("%s\n" % item)

def main(argv):
	# Create the parser.
	argparser = argparse.ArgumentParser(description='Filter out risky content categories: "XED", "GAYL", "PORN", "PROV", "DATE", "MINF", "HUMR", "REL", "LGBT".')

	# Add the arguments.
	argparser.add_argument("-i", "--inputurls", help="input url file, structured", required=True)
	argparser.add_argument("-l", "--localpath", help="path to citizenlab local cc.csv file", required=True)
	argparser.add_argument("-t", "--targetdir", help="path to store the results in", required=True)
	argparser.add_argument("-g", "--globalpath", help="path to citizenlab global.csv file")
	out = argparser.parse_args()
	run(out.inputurls, out.localpath, out.globalpath, out.targetdir)

if __name__ == "__main__":
   main(sys.argv[1:])