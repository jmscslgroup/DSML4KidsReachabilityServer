"""
This file contains the validation server code written in flask. The 
basic flow of the program is as follows:
    1) The root of the server recieves a POST request fromt the WebGME AddOn
    that contains the current JSON describing the path
    2) The path is transformed from the JSON into a list of states, with
    each state having the jumps in the object
    3) This state array is passed through to a jinja2 template that creates
    the dReach file
    4) The dReach file is tested and a validity response is passed back to 
    the AddOn
"""

from flask import Flask, request, Response
from jinja2 import Template
import logging
import subprocess

# Setup the logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

# Open the template and get all of the text from the
# template.
template_text = ""
template_file = "templates/catVehicleBasic.drh.jinja2"
with open(template_file) as t_f:
    template_text += "".join(t_f.readlines())

# Create the template
template = Template(template_text)
logging.debug("Successfully read in template")


class Motion:

    """Store a single state in the Hybrid Automata

    Attributes:
        flow (int): The flow of the motion
        jump (list): States that this state could jump to
        meta_name (str): Which abstract block type this is. Simple motion, if,
        etc.
    """

    def __init__(self):
        """Create the node with empty hybrid automata attributes
        """
        self.flow = -1
        self.jump = []
        self.meta_name = ""

    def __repr__(self):
        """Generate a string to describe the Motion

        Returns:
            str: Description of the object
        """
        return "\nFlow: " + \
               str(self.flow) + "\nJump: " + str(self.jump) + \
               "\nMeta: " + self.meta_name + "\n\n"


class MotionArray:

    """Store the overall hybrid automata. This is just basically just
    a list of motions with some functions to build the list and render
    the dReach template

    Attributes:
        motion_path (JSON): Path from the WebGME Addon
        states (list): Hybrid automata states
    """

    def __init__(self, motion_path):
        # Find the root node
        root_node = MotionArray._get_root_node(motion_path)
        logging.debug("Found root node @ " + root_node["id"])

        # Save the motion_path
        self.motion_path = motion_path

        # Create the states array
        self.states = []

        # Get all of the states from the motion path, starting at
        # the root
        logging.debug("Creating hybrid automata states")
        self._create_states(root_node)

        # Create all the jumps between possible states
        logging.debug("Creating jumps b/w hybrid automata")
        self._create_jumps()

    def render(self):
        """Render the current hybrid automata states
        
        Returns:
            str: dReach file representing the hybrid automata
        """
        return template.render(states=self.states)

    def _create_states(self, root_node_motion):
        """Recursively create a list of all the states that the path
        contains
        
        Args:
            root_node_motion (JSON): Root motion node
        """
        # Check if the node is a For block
        if root_node_motion["name"] == "For":
            # Log that a for block was found and what is contained inside of
            # it
            logging.debug("Found For with {} blocks inside to repeat {} times"
                          .format(len(root_node_motion["CodeToExecute"]),
                                  root_node_motion["Times"]))

            # Loop n times and add in the for block motion
            # to the array. Set the meta type for the first block
            meta_name = "FOR_OUTER"
            for _ in range(int(root_node_motion["Times"])):
                # For each loop the code to execute also needs to
                # be added.
                for motion in root_node_motion["CodeToExecute"]:
                    # Create the inner motion
                    inner_motion = Motion()
                    # Set the attributes
                    inner_motion.meta_name = meta_name
                    inner_motion.jump.append(len(self.states) + 1)
                    inner_motion.flow = motion

                    # Set the meta name for the next inner ones
                    meta_name = "FOR_INNER"

                    # Add the motion to the states list
                    self.states.append(inner_motion)

            # The last state always has last appended to it and doesn't
            # jump anywhere because this is taken care of in the jumps
            # method
            self.states[-1].meta_name += "_LAST"
            self.states[-1].jump = []

        # Check if the block is an if block
        elif root_node_motion["name"] == "If":
            # Log that an If has been found with x number of blocks
            # inside
            logging.debug("Found If with {} blocks inside"
                          .format(len(root_node_motion["CodeToExecute"])))

            # Set the meta name
            meta_name = "IF_OUTER"

            # Iterate through each motion within the for
            for motion in root_node_motion["CodeToExecute"]:
                # Create the motion
                inner_motion = Motion()

                # Stuff the motion with the information about the motion
                inner_motion.meta_name = meta_name
                inner_motion.jump.append(len(self.states) + 1)
                inner_motion.flow = motion

                # Set the new meta name
                meta_name = "IF_INNER"

                # Append the state to the list
                self.states.append(inner_motion)

            # The last If never has any jumps and has the _LAST
            # appended to the meta_name
            self.states[-1].jump = []
            self.states[-1].meta_name += "_LAST"

        # Check if the motion node is one of the "simple" motions
        elif root_node_motion["name"] in ["Straight", "Right", "Left",
                                          "ZigZagLeft", "ZigZagRight"]:
            # Log that a simple motion was found
            logging.debug("Found normal block")

            # Create and stuff the motion
            motion = Motion()
            motion.flow = root_node_motion["Type"]
            motion.meta_name = "SIMPLE"

            # Append the motion to the states array
            self.states.append(motion)

        # If the motion is none of the ones described above then log
        # that
        else:
            logging.debug("UNDEFINED MOTION:" + root_node_motion)

        # Check if the connections list is empty
        if root_node_motion["Connections"]:
            # Find the next node
            next_node = self.find_node(
                root_node_motion["Connections"][0]["targetId"])

            # If the next node is none raise an exception
            if next_node is None:
                raise Exception("Next state {} not found"
                                .format(root_node_motion["Connections"]
                                                        [0]["targetId"]))
            # If the next node is not none then recurse
            self._create_states(next_node)
             
        # If the connections list is empty then erase the last jump   
        else:
            self.states[-1].jump = []

    def _create_jumps(self):
        """Create the jumps between each state in the array. This is
        tricky because of the way that the If statements have to be
        handled. For each path do be tested the previous state has to be
        connected to the state in front of it and if that state is an if
        then it also has to be connected to the state in front of that
        if. And so on and so forth.
        """

        # Go through each state
        for i, state in enumerate(self.states[:-1]):
            # If the meta_name contains the keyword LAST or SIMPLE then
            # it will need a connection. If this is not true then just 
            # skip over the block
            if not "LAST" in state.meta_name and not "SIMPLE" in state.meta_name:
                continue

            # Log that state i is getting its connections
            logging.debug("Connecting state {}".format(i))

            # Get the meta type of the next block and log the next
            # meta_type
            next_block_meta_type = self.states[i + 1].meta_name
            logging.debug("State {} next block type: {}"
                          .format(i, next_block_meta_type))

            # If the next block's meta type is IF_OUTER, IF_OUTER_LAST
            # or IF_INNER_LAST then that means that the next block is
            # an if and as such will need to be treated in a special 
            # manner. The current block will need to be connected to 
            # both this next if block and every block after it that is
            # an if and finally to the next block that isn't an if. This
            # is so dReach can explore every single path to find if at
            # least one is unsat
            jump_i = 1
            if next_block_meta_type in ["IF_OUTER", "IF_OUTER_LAST",
                                        "IF_INNER_LAST"]:

                # Loop while the next block is not a simple block that 
                # the block that is being connected can terminate on. 
                # But do not exceed the length of the state array
                while (next_block_meta_type not in
                       ["FOR_OUTER", "SIMPLE"] and 
                       jump_i + i < len(self.states)):
                    # If the next block is an if inner skip it. These
                    # are already connected up
                    if next_block_meta_type == "IF_INNER":
                        continue

                    # If the next block is an IF then connect to it
                    # and continue on
                    if next_block_meta_type in ["IF_OUTER",
                                                "IF_OUTER_LAST"]:
                        logging.debug("Connecting state {} to {}"
                                      .format(i, self.states[i + jump_i].meta_name))
                        state.jump.append(i + jump_i)

                    # Get the next block type
                    jump_i += 1
                    next_block_meta_type = self.states[i + jump_i].meta_name
                    logging.debug("State {} next block type: {}"
                                  .format(i, next_block_meta_type))

                # TODO: If if is the last block

                logging.debug("Finished If connections")

            # If the next blocks meta type is SIMPLE or FOR_OUTER then
            # it is a simple jump to the next block
            if (next_block_meta_type in ["FOR_OUTER", "FOR_INNER",
                                         "FOR_OUTER_LAST",
                                         "FOR_INNER_LAST", "SIMPLE"]):
                state.jump.append(i + jump_i)
                logging.debug("Connecting state {} to {}"
                              .format(i,
                                      self.states[i + jump_i].meta_name))
            # Log all of the connections of the state
            logging.info("State: {} has connections {}"
                         .format(i, state.jump))

        # The last state jumps to the goal state. This is a naive way of doing
        # this and TODO: new way of deciding the jumps
        self.states[-1].jump = [-1]

    def find_node(self, node_id):
        """Given a node ID return the motion JSON block

        Args:
            node_id (str): Node id (e.g. "I/x/")

        Returns:
            Motion JSON or None: Motion block if it is found, None else
        """
        # Search through each motion block in the path
        for motion in self.motion_path["pathModel"]["motion"]:
            # If the ids are the same then return the motion block
            if motion["id"] == node_id:
                return motion

        # If this method hasn't returned by now return None to signify
        # no block was found
        return None

    @staticmethod
    def _get_root_node(motion_path):
        """Get the root node of the path

        Args:
            motion_path (Path JSON): The whole path object

        Returns:
            Motion JSON: Root node of the path

        Raises:
            ValueError: If the path has no root
        """
        # Search through every motion in the path
        for motion in motion_path["pathModel"]["motion"]:
            # If the motion is the starting motion
            if motion["isStart"]:
                # Return it
                return motion

        # If no motion was returned raise a ValueError
        raise ValueError("Motion Path must have a start node")


app = Flask(__name__)


@app.route("/", methods=["POST"])
def validate_path():
    """Upon an HTTP request to the root of the webserver
    first ensure that the request is good and then process
    the JSON into a drh file, run it through d-reach, and
    then return how valid the path is
    Returns:
        Flask.Response: JSON response with the
    """

    # Check that the request is actually valid JSON
    print(request.data)
    if not request.json:
        # If not return a 400 error
        logging.debug("Not valid JSON")
        return Response("{'status':'failed', 'validity':null}",
                        status=400, mimetype="application/json")

    try:
        # Template the JSON
        ma = MotionArray(request.json)
        with open("dReachTempFile.drh", "w+") as f:
            f.write(ma.render())

        # Run dReach
        dReach_command = "dReach -z -k {} ".format(len(ma.states)) + \
                         "dReachTempFile.drh --visualize"
        print(dReach_command)

        p = subprocess.Popen(dReach_command,
                             stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()

        # Determine if the output is SAT in every case that a goal
        # is reached
        is_sat = True

        if "SAT" in str(output):
            output_split = output.split("\n")
            for i, line in enumerate(output_split):
                if "SMT: " in line and "SAT" not in output_split[i + 1]:
                    print(output_split[i + 1])
                    is_sat = False
        else:
            is_sat = False

        if is_sat:
            logging.debug("SAT")
            return Response("{'status':'succeeded', 'validity': true}",
                            status=201, mimetype="application/json")
        else:
            logging.debug("UNSAT")
            return Response("{'status':'succeeded', 'validity': false}",
                            status=201, mimetype="application/json")

    except Exception as e:
        logging.debug("Errored out: {}".format(str(e)))

        return Response("{'status':'failed', 'validity':null}",
                        status=400, mimetype="application/json")


if __name__ == "__main__":
    app.run(host='0.0.0.0')
