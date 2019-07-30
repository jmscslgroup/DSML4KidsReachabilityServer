from flask import Flask, request, json, Response
from jinja2 import Template
import logging
import subprocess

# Setup the logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

# Open the template and get all of the text from the
# template.
template_text = ""
template_file = "/home/alex/CAT/ReachabilityAnalysis/" + \
                "ReachabilityServer/templates/catVehicleBasic.drh.jinja2"
with open(template_file) as t_f:
    template_text += "".join(t_f.readlines())

template = Template(template_text)

logging.debug("Successfully read in template")


class Motion:
    def __init__(self):
        """Create the node with empty hybrid automata attributes
        """
        self.flow = ""
        self.jump = []
        self.meta_name = ""

    def __repr__(self):
        return "\nFlow: " + \
               str(self.flow) + "\nJump: " + str(self.jump) + \
               "\nMeta: " + self.meta_name + "\n\n"


# TODO: Better name and refactor
class MotionArray:
    def __init__(self, motion_path):
        # Find the root node
        root_node = MotionArray._get_root_node(motion_path)
        logging.debug("Found root node @ " + root_node["id"])

        # Save the motion_path
        self.motion_path = motion_path

        # Create the states array
        self.states = []

        # Recursively search down the motion path and create the tree
        logging.debug("Creating hybrid automata states")
        self._create_states(root_node)
        logging.debug("Creating jumps b/w hybrid automata")
        self._create_jumps()

    def render(self):
        return template.render(states=self.states)

    def _create_states(self, root_node_motion):
        # Check if the node is a For block
        if root_node_motion["name"] == "For":
            logging.debug("Found For with {} blocks inside to repeat {} times"
                          .format(len(root_node_motion["CodeToExecute"]),
                                  root_node_motion["Times"]))
            # Loop n times and add in the for block motion
            # to the array
            meta_name = "FOR_OUTER"
            for _ in range(int(root_node_motion["Times"])):
                # For each loop the code to execute also needs to
                # be added.
                for motion in root_node_motion["CodeToExecute"]:
                    inner_motion = Motion()

                    inner_motion.meta_name = meta_name
                    inner_motion.jump.append(len(self.states) + 1)
                    inner_motion.flow = motion
                    # inner_motion.invt.append("Not Yet Implemented")

                    meta_name = "FOR_INNER"

                    self.states.append(inner_motion)

            self.states[-1].meta_name += "_LAST"
            self.states[-1].jump = []

        # Check if the block is an if block
        elif root_node_motion["name"] == "If":
            logging.debug("Found If with {} blocks inside"
                          .format(len(root_node_motion["CodeToExecute"])))
            meta_name = "IF_OUTER"

            for motion in root_node_motion["CodeToExecute"]:
                inner_motion = Motion()
                inner_motion.meta_name = meta_name
                inner_motion.jump.append(len(self.states) + 1)
                inner_motion.flow = motion
                # inner_motion.invt.append("Not Yet Implemented")

                meta_name = "IF_INNER"
                self.states.append(inner_motion)

            self.states[-1].jump = []
            self.states[-1].meta_name += "_LAST"

        # If the block is neither the
        elif root_node_motion["name"] in ["Straight", "Right", "Left"]:
            logging.debug("Found normal block")

            motion = Motion()
            motion.flow = root_node_motion["Type"]
            # motion.invt.append("Not Yet Implemented")
            motion.meta_name = "SIMPLE"
            self.states.append(motion)

        else:
            logging.debug("UNDEFINED MOTION:" + root_node_motion)

        # Progress onto the next block if one exists
        if root_node_motion["Connections"]:
            next_node = self.find_node(
                root_node_motion["Connections"][0]["targetId"])

            if next_node is not None:
                self._create_states(next_node)
                return
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
            # print(state)
            # If the meta_name contains the keyword LAST or SIMPLE then
            # it will need a connection.
            if "LAST" in state.meta_name or "SIMPLE" in state.meta_name:
                logging.debug("Connecting state {}".format(i))
                # Get the meta type of the next block
                next_block_meta_type = self.states[i + 1].meta_name
                logging.debug("State {} next block type: {}"
                              .format(i, next_block_meta_type))

                # If the next block is an IF_OUTER then add a
                # connection to the IF_OUTER, and all IF_OUTERS
                # after it until a FOR_OUTER or SIMPLE block is reached
                jump_i = 1
                if next_block_meta_type in ["IF_OUTER", "IF_OUTER_LAST",
                                            "IF_INNER_LAST"]:

                    while (next_block_meta_type not in
                           ["FOR_OUTER", "SIMPLE"] and
                           jump_i + i < len(self.states)):
                        # If the next block is an if inner skip it
                        if next_block_meta_type == "IF_INNER":
                            continue

                        if next_block_meta_type in ["IF_OUTER",
                                                    "IF_OUTER_LAST"]:
                            logging.debug("Connecting state {} to {}"
                                          .format(i, self.states[i + jump_i].meta_name))
                            state.jump.append(i + jump_i)

                        jump_i += 1
                        next_block_meta_type = self.states[i + jump_i].meta_name
                        logging.debug("State {} next block type: {}"
                                      .format(i, next_block_meta_type))

                    # TODO: If if is the last block

                    logging.debug("Exited Loop")

                # If the next blocks meta type is SIMPLE or FOR_OUTER then
                # it is a simple jump to the next block
                if (next_block_meta_type in ["FOR_OUTER", "FOR_INNER",
                                             "FOR_OUTER_LAST",
                                             "FOR_INNER_LAST", "SIMPLE"]):
                    state.jump.append(i + jump_i)
                    logging.debug("Connecting state {} to {}"
                                  .format(i,
                                          self.states[i + jump_i].meta_name))

            logging.info("State: {} has connections {}"
                         .format(i, state.jump))

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

        if "SAT" in str(output):
            return Response("{'status':'succeeded', 'validity': true}",
                    status=201, mimetype="application/json")
        else:
            return Response("{'status':'succeeded', 'validity': false}",
                    status=201, mimetype="application/json")
        # Return the dReach response
        # TODO: Return a suggestion


    except Exception as e:
        logging.debug("Errored out: {}".format(str(e)))

        return Response("{'status':'failed', 'validity':null}",
                        status=400, mimetype="application/json")

