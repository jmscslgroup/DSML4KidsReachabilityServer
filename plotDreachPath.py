#!/usr/bin/python3

import json
from typing import Dict
from sys import argv
import matplotlib.pyplot as plt
from math import floor, log


def get_traces(data: Dict, resolution: int=10):
    """Get the movement of the car's x and y position from the dReach
    smt2.json files at a given "resolution"
    
    Args:
        data (Dict): dReach smt2.json data
        resolution (int, optional): How fine the movement in each mode
        should be
    
    Returns:
        ([], []): A tuple containing the x movement and the y movement
        respectfully.
    """
    # Hold the x and y variables in an array
    x = []
    y = []

    # Itterate through each step of the model
    for trace in data["traces"]:
        # The last trace is always None so break on the last one
        if trace is None:
            break

        # Itterate through each variable in the current step
        for var_in_mode in trace:
            # The *_last varaibles aren't important to plot, they
            # are just used for keeping track of when the states need
            # to change
            if "last" in var_in_mode["key"]:
                continue

            # Hold all of the values in an array
            values = []

            # Get the top and bottom values of the variable in the
            # current state
            first = round(var_in_mode["values"][0]["enclosure"][0])
            last = round(var_in_mode["values"][-1]["enclosure"][-1])

            # Find the difference
            diff = last - first

            # If the diff is 0 then just put resolution of the same value in
            # the array
            if diff == 0:
                values = [first for _ in range(resolution)]
            # If the diff is not 0 then increment the values from first
            # to last with a jump of the diff / resolution. This will be
            # negative if the last is greater than first
            else:
                # Start off the increment as 0
                inc = 0

                # Loop while the values array is not filled
                while len(values) < resolution:
                    # Append the value rounded to the floor of the log_10
                    # of the resolution so that there is enough decimal
                    # resolution to distinguish the values
                    values.append(round(first + inc,
                                        floor(log(resolution, 10))))
                    inc += diff / resolution

            # Extend the values arrays depending on the keys name
            if "x" in var_in_mode["key"]:
                x.extend(values)
            else:
                y.extend(values)

        # Return the x and y arrays
        return x, y


# Store the X and Y position of the car in arrays
x = []
y = []

# Store the data
data = None

# Try and read in the JSON file that is passed in
try:
    # Open the JSON file that is passed in
    with open(argv[1], "r") as smt2_json:
        # Read all of the data
        data = json.loads("".join(smt2_json.readlines()))
except Exception as e:
    # If the JSON file was not read then print out what happened and exit
    print("Error reading the JSON file... " +
          "Are you sure there's anything in it? " +
          "(err: {})".format(e))
else:
    # Check that the data is not None
    if data is None:
        print("Error in reading the JSON file... " +
              "Are you sure there's anything in it? " +
              "(err: data was None)")
    else:
        # If the data was read in then process it
        x, y = get_traces(data)

        # Plot the data with gridlines
        plt.plot(x, y)
        plt.grid(True, "both")
        plt.show()
