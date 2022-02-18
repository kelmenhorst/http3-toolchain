#!/usr/bin/env python3
import argparse
import sys
import os
import subprocess
from pathlib import Path

import generate_txt_input
import check_http3
import aggregate
import filter_categories
import resolve

# Handles 5 preprocessing steps. (check out README)

def main(argv):
    # Create the parser.
    argparser = argparse.ArgumentParser(description='Handles 5 preprocessing steps. (check out README)')
    # Add the arguments.
    argparser.add_argument("-l", "--listdir", help="path to test-lists/ directory", required=True)
    argparser.add_argument("-cc", "--countrycode", help="country code", required=True)
    argparser.add_argument("-t", "--targetdir", help="target directory to store generated input files", required=True)
    argparser.add_argument("-g", "--globallist", help="consider global test list", action='store_true')
    argparser.add_argument("-c", "--column", help="column with urls in the csv file, default 0")
    argparser.add_argument("-v", "--verbose", help="verbose output", action='store_true')
    args = argparser.parse_args()
    cc = args.countrycode.lower()

    print("Step 1: Extracts url strings from csv tables...")

    # generate_txt_input.py
    targetdir = os.path.join(args.targetdir, "raw")
    Path(targetdir).mkdir(parents=True, exist_ok=True)
    generate_txt_input.run(cc, targetdir, args.listdir, args.column)
    urls_file = os.path.join(targetdir, cc+".txt")
    # ./raw/cc.txt

    print("Step 1: Done.")

    print("Step 2: HTTP Get the input websites and inspect the Alt-Svc header for h3 support announcement...")

    # check_http3.py
    targetdir = os.path.join(args.targetdir,"http3")
    Path(targetdir).mkdir(parents=True, exist_ok=True)
    check_http3.run(urls_file, targetdir, args.verbose)
    http3_file = os.path.join(targetdir, cc+"_http3.txt")
    # ./http3/cc_http3.txt

    print("Step 2: Done.")

    print("Step 3 (optional): Merge multiple url lists, and delete duplicates...")

    # aggregate.py (optional)
    if args.globallist:
        global_http3_file = os.path.join(targetdir, "global_http3.txt")
        files = [http3_file, global_http3_file]
        aggregate.run(files)
        http3_file = os.path.join(targetdir, cc+"_http3_global_http3.txt")
        # ./txts/cc_http3_global_http3.txt

    print("Step 3: Done.")

    print("Step 4: Filter out risky content categories: XED, GAYL, PORN, PROV, DATE, MINF, REL, LGBT...")

    # filter_categories.py (optional input file?)
    targetdir = os.path.join(args.targetdir,"filtered")
    Path(targetdir).mkdir(parents=True, exist_ok=True)
    local_filepath = os.path.join(args.listdir, "lists", cc+".csv")
    global_filepath = os.path.join(args.listdir, "lists", "global.csv")
    filter_categories.run(http3_file, local_filepath, global_filepath, targetdir)
    http3_file = os.path.join(targetdir, os.path.basename(http3_file)+".filtered.txt")

    print("Step 4: Done.")

    print("Step 5: Resolve IP addresses with dot://8.8.8.8...")

    # resolve.py
    prefix = cc
    if args.globallist:
        prefix += "_global"
    prefix += "_http3_filtered"
    targetdir = os.path.join(args.targetdir,"resolved")
    Path(targetdir).mkdir(parents=True, exist_ok=True)
    resolve.run(http3_file, prefix, targetdir)

    print("Step 5: Done.")



if __name__ == "__main__":
    main(sys.argv[1:])