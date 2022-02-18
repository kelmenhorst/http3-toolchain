#!/usr/bin/env python3
import sys
import subprocess
import argparse
import os
import requests


def run(input_file, targetdir, verbose=True):
    in_name, suffix = os.path.basename(input_file).split(".")
    out_name = os.path.join(targetdir, in_name+"_http3."+suffix)

    with open(input_file, "r") as in_file:
        for url in in_file:
            if verbose:
                print("trying", url)
            try:
                r = requests.get(url, timeout=5)
            except:
                print("HTTP get failed")
                continue
            if not "Alt-Svc" in r.headers:
                continue
            alt_svc = r.headers["Alt-Svc"]
            final_url = r.url
            if final_url.endswith("%0A"):
                final_url = final_url.replace("%0A", "")
            if "h3=" in alt_svc:
                with open(out_name, "a+") as out_file:
                    out_file.write(final_url+"\n") # r.url is the URL of the final response (after redirects)
            elif "h3-29=" in alt_svc:
                with open(out_name, "a+") as out_file:
                    out_file.write(final_url+"\n") # r.url is the URL of the final response (after redirects)
                

def main(argv):
    # Create the parser.
    argparser = argparse.ArgumentParser(description='Runs miniooni urlgetter with HTTP3Enabled=true and inspects output to filter url list for HTTP3 support.')
    # Add the arguments.
    argparser.add_argument("-i", "--inputfile", help="url list, structured", required=True)
    argparser.add_argument("-t", "--targetdir", help="name of the target directory", required=True)
    argparser.add_argument("-v", "--verbose", help="verbose output", action='store_true')
    args = argparser.parse_args()
    run(args.inputfile, args.targetdir, args.verbose)


if __name__ == "__main__":
    main(sys.argv[1:])