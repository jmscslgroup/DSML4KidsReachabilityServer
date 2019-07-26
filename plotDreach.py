#! /usr/bin/python3

import json
from sys import argv
import logging
from typing import Dict

import seaborn as sns; sns.set()
import matplotlib.pyplot as plt

# Initialize logging
logging.basicConfig(level=logging.INFO)

def open_json(file_name: str) -> Dict:
	"""
	Open the a specified json file
	"""
	with open(file_name, "r") as f:
		# Return the joined file as a JSON object
		return json.loads("".join(f.readlines()))

# Open the json file in the first argument
# TODO: add elegent error handling
smt2_json = open_json(argv[1])

# In the dReach output files the change in all of the variables
# in a certain state is captured in a "trace", each trace then
# has multiple variables within it each with list of the 
# changes of the variable over time
for trace in smt2_json["traces"]:
	# Check that the trace is not none
	if trace is None:
		break

	y = []
	legend = []
	x = []

	# For each variable within the state
	for sub_trace in trace:
		if not (sub_trace["key"][0] == "x" or sub_trace["key"][0] == "y"):
			continue
		# Log that we are plotting the variable in the mode
		# TODO: add how many times we have visited this node?
		logging.info("Plotting {} in mode {}"
			.format(sub_trace["key"], sub_trace["mode"]))

		# Gather information for the plot title
		plot_title = sub_trace["key"] + " in mode " + str(sub_trace["mode"])

		plt.ylabel(sub_trace["key"])
		plt.xlabel("time")

		# Intialize lists for the plotting data
		time_values = []
		enclosure = []

		for value in sub_trace["values"]:
			time_values.append(value["time"][0])
			enclosure.append(value["enclosure"][0])

			if sub_trace["key"][0] == "x":
				x.append(value["enclosure"][0])
			else:
				y.append(value["enclosure"][0])

		ax = sns.lineplot(x=time_values, y=enclosure)
		ax.set_title(plot_title)
		ax.legend(["x", "y"])
		plt.savefig(plot_title + ".png")	
