#!/usr/bin/env python3
import sys
import subprocess
import argparse
import os


def run(input_file, miniooni_path, targetdir, verbose=True):
    in_name, suffix = os.path.basename(input_file).split(".")
    out_name = os.path.join(targetdir, in_name+"_http3."+suffix)

    with open(input_file, "r") as in_file:
        for url in in_file:
            cmd = [miniooni_path, "-n", "-N", "-i", url.strip(), "-O", "HTTP3Enabled=true", "urlgetter"]
            out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out_str = out.stdout.decode("utf-8")
            if verbose:
                print(out_str)
            if "<warn> measurement failed" in out_str:
                continue
            with open(out_name, "a+") as out_file:
                out_file.write(url)

def main(argv):
    # Create the parser.
    argparser = argparse.ArgumentParser(description='Runs miniooni urlgetter with HTTP3Enabled=true and inspects output to filter url list for HTTP3 support.')
    # Add the arguments.
    argparser.add_argument("-i", "--inputfile", help="url list, structured", required=True)
    argparser.add_argument("-m", "--miniooni_path", help="path to miniooni executable", required=True)
    argparser.add_argument("-t", "--targetdir", help="name of the target directory", required=True)
    argparser.add_argument("-v", "--verbose", help="verbose output", action='store_true')
    args = argparser.parse_args()
    run(args.inputfile, args.miniooni_path, args.targetdir, args.verbose)



if __name__ == "__main__":
    main(sys.argv[1:])