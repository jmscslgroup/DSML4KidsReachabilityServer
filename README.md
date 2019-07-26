# What does this Repo hold?
This repository holds the server that is used to validate the DSML code gerenated by the "DSML 4 Kidz" modelling language. It works by combining a server written in Flask with a reachability analysis tool called dReach. The dReach code is generated in Python and then run on the host machine. The result is then returned in a JSON object to the client.

# Prerequisites 
1. dReal/dReach 3
2. Python 3
   This should come pre-installed on most linux machines. To test if Python 3 is installed run `python3` in the terminal. If it is not installed you can download it from the (Python Website)[python.org]
3. Python 3 Virtual Env
