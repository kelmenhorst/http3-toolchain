#!/usr/bin/env python3
import pandas
import os
import sys
import argparse

# Extracts url strings from csv tables.

def run(countrycode, targetdir, rootdir, column):
	cc = countrycode.lower()
	col = 0
	if column:
		col = int(column)

	# Gather all input files.
	inputfile = "test-lists/lists/"+cc+".csv"
	if rootdir:
		if not rootdir.endswith("/"):
			rootdir = rootdir + "/"
		inputfile = rootdir + "lists/"+cc+".csv"
	outputfile = os.path.join(targetdir, cc+".txt")
  
	# Write urls to text file.
	with open(inputfile, "r") as ifile:
		df = pandas.read_csv(ifile, header=None, usecols=[col])
		urls = df[col][1:]
		for url in urls:
			if not (url.startswith("http://") or url.startswith("https://")):
				url = "https://"+url
			with open(outputfile, "a") as ofile:
				if url.startswith("http://"):
					url = url.replace("http://", "https://", 1)
				ofile.write(url+"\n")


def main(argv):
	# Create the parser.
	argparser = argparse.ArgumentParser(description='Extracts url strings from csv tables.')

	# Add the arguments.
	argparser.add_argument("-cc", "--countrycode", help="country code", required=True)
	argparser.add_argument("-t", "--targetdir", help="name of the target directory", required=True)
	argparser.add_argument("-c", "--column", help="column")
	argparser.add_argument("-r", "--rootdir", help="path to test-lists/ directory")
	out = argparser.parse_args()
	run(out.countrycode, out.targetdir, out.rootdir, out.column)

if __name__ == "__main__":
   main(sys.argv[1:])
