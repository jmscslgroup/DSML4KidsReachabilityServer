# What does this Repo hold?
This repository holds the server that is used to validate the DSML code gerenated by the "DSML 4 Kidz" modelling language. It works by combining a server written in Flask with a reachability analysis tool called dReach. The dReach code is generated in Python and then run on the host machine. The result is then returned in a JSON object to the client.

# Prerequisites 
1. dReal/dReach 3
	 Installation for dReal/dReach is pretty self-explanitory. The only hiccup is that gcc-4.9 is not avaliable on the latest LTS Ubnutu. So I just compiled it with the gcc/g++ that comes with Ubuntu 18.04. Installation instructions [here](https://github.com/dreal/dreal3/blob/master/doc/ubuntu-gcc.md)
2. Python 3

   	This should come pre-installed on most linux machines. To test if Python 3 is installed run `python3` in the terminal. If it is not installed you can download it from the [Python Website](python.org)

3. Python 3 Virtual Env

    Python 3 does not come preloaded with the virtual environment. To install this on Debian or Debian-derivatives

# Running the Server (Development)
1. Create a virtual env in this folder by running `python3 -m venv ./venv`
2. Activate the virtual env by running `source ./venv/bin/activate{.bash/.fish/.zsh}`
3. Install the packages by running `pip install -r requirements.txt`
4. Export the flask environment to tell flask what to run `export FLASK_APP=DSMLVerificationServer.py`
5. Run flask `flask run` (`flask run --reload` if you are developing the server)
