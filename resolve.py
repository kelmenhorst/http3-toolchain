#!/usr/bin/env python3
import sys
import json
import os
import socket
import urllib.request
import json
import argparse
from urllib.parse import urlparse

sni_alt = "https://www.cloudflare.com"
sni_alt_name = "www.cloudflare.com"
sni_alt_short = "cloudflare"
sni_alt_cache = "www.cloudflare.com 104.16.124.96"

resolver = "dot://8.8.8.8:853"


def run(input_file, output_prefix, target_dir):
	output_cacheddns = os.path.join(target_dir, output_prefix+"_cacheddns.txt")
	endpoints = []

	with open(output_cacheddns, "w") as output:
		with open(input_file, "r") as urls:
			for url in urls:
				url = url.rstrip()
				if url == "":
					continue
				print(url)
				domain = urlparse(url).netloc
				with urllib.request.urlopen(("https://dns.google/resolve?name={}&type=A").format(domain)) as u:
					data = json.loads(u.read().decode())
				if data["Status"] == 0 :
					for ans in data["Answer"]:
						if ans["type"] == 1:
							ip = ans["data"]
							print(ip)
							break
					if not ip:
						print("warning! ", domain, domain.split("/")[0])
						continue	
				else:
					print("warning! ", domain, domain.split("/")[0])
					continue
				dns_cache = domain.split("/")[0] + " " + str(ip)
				endpoints.append(ip)
				output.write(url+"-----"+ip+"\n")


def main(argv):
	# Create the parser.
	argparser = argparse.ArgumentParser(description='Resolve IP addresses with dot://8.8.8.8.')

	# Add the arguments.
	argparser.add_argument("-i", "--inputfile", help="url list, structured", required=True)
	argparser.add_argument("-p", "--prefix", help="name prefix of the output file")
	out = argparser.parse_args()
	run(out.inputfile, out.outputfile)


if __name__ == "__main__":
   main(sys.argv[1:])