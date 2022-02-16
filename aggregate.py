#!/usr/bin/env python3
import sys
import os.path
import argparse

# Merges multiple url lists, and deletes duplicates.

def run(files):
	print(files)
	lines = []
	outname = ""

	# Sum all file contents and combine output file name from input names (i1_i2_i3.txt)
	for file in files:
		outname += os.path.basename(file).replace(".txt", "")+"_"
		with open(file, 'r') as f:
			for line in f:
				lines.append(line)
	outname = outname[:-1]+".txt"
	outname = os.path.join(os.path.dirname(file), outname)
	uniques = list(dict.fromkeys(lines))

	cropped_uniques = []
	final_uniques = []
	for u in uniques:
		new_u = u.replace("/\n", "\n")
		new_u = u.replace("https://", "", 1)
		new_u = u.replace("www.", "")
		if new_u in cropped_uniques:
			print(new_u)
			continue
		cropped_uniques.append(new_u)
		final_uniques.append(u)
	print(len(cropped_uniques))
	with open(outname, 'w') as f:
			for l in final_uniques:
				f.write("%s" % l)


if __name__ == "__main__":
	if "-h" in sys.argv:
		print("usage: aggregate.py [-h] FILE1 FILE2 [FILE3 ...] \n \nMerge multiple url lists and delete duplicates.")
		sys.exit()

	run(sys.argv[1:])