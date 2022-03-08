#!/usr/bin/env python3
import pandas
import sys
import urllib.request
import os
import argparse
from urllib.parse import urlparse

# Filter out risky content categories: "XED", "GAYL", "PORN", "PROV", "DATE", "MINF", "REL", "LGBT"
# Input:  path_to_local_citizenlab input_txt_file

with urllib.request.urlopen("https://raw.githubusercontent.com/kush789/How-India-Censors-The-Web-Data/master/potentially_blocked_unique_hostnames.txt") as url:
			cis_india = (url.read().decode().splitlines())

safe_global = [
	"https://consent.google.com/ml?continue=https://news.google.com/&gl=DE&hl=en-US&pc=n&src=1",
	"https://accounts.google.com/ServiceLogin?passive=1209600&osid=1&continue=https://plus.google.com/%250A&followup=https://plus.google.com/%250A",
	"https://en.goldenrivieracasino.com/%0A",
	"https://www.theregister.com/%0a",
	"https://consent.youtube.com/ml?continue=https://www.youtube.com/%250A&gl=DE&hl=de&pc=yt&uxe=23983171&src=1",
	"https://www.ifacetimeapp.com",
	"https://messages.google.com/web/?redirected=true",
	"https://support.google.com/publicalerts",
	"https://www.dcard.tw",
	]



def run(input_urls_filepath, cc, use_globallist, target_dir, categories):
	cc_url = "https://raw.githubusercontent.com/citizenlab/test-lists/master/lists/"+cc+".csv"
	df = pandas.read_csv(cc_url, header=None, usecols=[0, 1])

	if use_globallist:
		global_url = "https://raw.githubusercontent.com/citizenlab/test-lists/master/lists/global.csv"
		df_global = pandas.read_csv(global_url, header=None, usecols=[0, 1])
		df = pandas.concat([df, df_global], ignore_index=True)

	not_found = []
	ok = []
	with open(input_urls_filepath, "r") as urlsfile:
		for url in urlsfile:
			url = url.rstrip()
			ok.append(url)
			if url.endswith("/"):
				url = url[:-1]
			domain = urlparse(url).netloc
			url = url.replace("https://", "", 1)
			if "spankbang" in url or "sexual" in url or "lushstories" in url:
					ok = ok[:-1]
					print("removed", "individual", url)
					continue
			index = df.index[df[0].str.contains(domain)].tolist()
			if not len(index):
				for safeu in safe_global:
					if url in safeu:
						break
				else:
					print("not found: ", url)
					not_found.append(url)
					ok = ok[:-1]
				continue
			for ix in range(len(index)):
				category = (df[1][index[int(ix)]]).upper()
				# remove websites from these categories
				for c in categories:
					if category.upper() in c or c in category.upper():
						print("removed", category, url, ok[-1])
						ok = ok[:-1]
						break
				else:
					continue  # only executed if the inner loop did NOT break
				break 


	# Print urls that have not been found in source files.
	print(not_found)

	out_file = os.path.join(target_dir, os.path.basename(input_urls_filepath)+".filtered.txt")
	with open(out_file, "w") as filteredfile:
		for item in ok:
			filteredfile.write("%s\n" % item)

def main(argv):
	# Create the parser.
	argparser = argparse.ArgumentParser(description='Filter out certain risky content categories, e.g. "XED", "GAYL", "PORN", "PROV", "DATE", "MINF", "HUMR", "REL", "LGBT".')

	# Add the arguments.
	argparser.add_argument("-i", "--inputurls", help="input url file, structured", required=True)
	argparser.add_argument("-cc", "--countrycode", help="country code", required=True)
	argparser.add_argument("-t", "--targetdir", help="path to store the results in", required=True)
	argparser.add_argument("-c", "--categories", help="the category codes to filter out, separated by whitespaces", required=True)
	argparser.add_argument("-g", "--globallist", help="consider global test list", action='store_true')
	out = argparser.parse_args()
	
	cc = out.countrycode.lower()
	categories = out.categories.split(" ")
	
	run(out.inputurls, cc, out.globallist, out.targetdir, categories)

if __name__ == "__main__":
   main(sys.argv[1:])