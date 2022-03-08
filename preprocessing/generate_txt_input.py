#!/usr/bin/env python3
import pandas
import os
import sys
import argparse

# Extracts url strings from csv tables in github.com/citizenlab/test-lists.

def run(countrycode, targetdir):
	cc = countrycode.lower()
	outputfile = os.path.join(targetdir, cc+".txt")

	# Get the test list from Github.
	input_url = "test-lists/lists/"
	url = "https://raw.githubusercontent.com/citizenlab/test-lists/master/lists/"+cc+".csv"
	df = pandas.read_csv(url, header=None, usecols=[0])
	urls = df[0][1:]

	# Clean urls and write them into the txt file.
	for url in urls:
		if not (url.startswith("http://") or url.startswith("https://")):
			url = "https://"+url
		if url.startswith("http://"):
			url = url.replace("http://", "https://", 1)
		with open(outputfile, "a") as ofile:
			ofile.write(url+"\n")


def main(argv):
	# Create the parser.
	argparser = argparse.ArgumentParser(description='Extracts url strings from csv tables in github.com/citizenlab/test-lists.')

	# Add the arguments.
	argparser.add_argument("-cc", "--countrycode", help="country code", required=True)
	argparser.add_argument("-t", "--targetdir", help="name of the target directory", required=True)
	out = argparser.parse_args()
	run(out.countrycode, out.targetdir)

if __name__ == "__main__":
   main(sys.argv[1:])
