import subprocess
import sys
import tempfile

from ucca.core import Passage
from ucca.ioutil import file2passage
from ucca.layer0 import Layer0
from ucca.layer1 import Layer1

from relation_extraction_utils.internal.ucca_types import UccaParsedPassage, UccaEdge, UccaNode, UccaTerminalNode


class TupaParser2(object):
    """

    Attributes
    ----------
    Methods
    -------

    """

    def __init__(self, tupa_utility_path, model_prefix):
        """

        Parameters
        ----------
        """

        self._tupa_utility_path = tupa_utility_path
        self._model_prefix = model_prefix


    def parse_sentences(self, sentences):

        parsed_passages = []

        # the command tempfile.mkdtemp() leaves the directory in place ..
        # consider replacing with 'with tempfile.TemporaryDirectory() as dir_name',
        # which will created the directory and then delete it with all it's contents
        # at the end of the 'with' block

        dir_name = tempfile.mkdtemp()
        print("using directory {} for input to and output from 'python -m tupa command'".format(dir_name),
              file=sys.stderr)

        for count, sentence in enumerate(sentences):
            input_path = '{}/file_{}'.format(dir_name, count)
            with open(input_path, 'w') as input:
                input.write(sentence)

        command = 'cd {}; python -m tupa {} -m {} -p parsed_ -o {}'.format(self._tupa_utility_path,
                                                                           dir_name,
                                                                           self._model_prefix, dir_name)
        result = subprocess.run(
            [command],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True)

        if result.returncode != 0:
            print("commnd '{}' failed ".format(command), file=sys.stderr)
            print("it\'s output was:\n{}".format(result.stdout), file=sys.stderr)

            # return empty list of parsed outputs
            return []


        for count, _ in enumerate(sentences):
            output_file = '{}/parsed_file_{}_0.xml'.format(dir_name, count)
            internal_parsed_passage = file2passage(output_file)
            parsed_passage = TupaParser2.__get_ucca_parsed_passage_from_passage(internal_parsed_passage)

            parsed_passages.append(parsed_passage)

        return parsed_passages


    @staticmethod
    def __get_ucca_parsed_passage_from_passage(passage: Passage):
        ucca_parsed_passage = UccaParsedPassage()

        ucca_parsed_passage.terminals = []
        ucca_parsed_passage.non_terminals = []
        ucca_parsed_passage.edges = []

        ucca_node_lookup = {}

        layer0 = next(layer for layer in passage.layers if isinstance(layer, Layer0))
        layer1 = next(layer for layer in passage.layers if isinstance(layer, Layer1))

        for node in layer0.all:
            edge_tags_in = [edge.tag for edge in node.incoming]
            token_id = int(node.ID.split('.')[1])  # :)
            terminal_node = UccaTerminalNode(node.ID, edge_tags_in, token_id, node.text, node.extra.get('lemma', '-'))
            ucca_parsed_passage.terminals.append(terminal_node)
            ucca_node_lookup[node.ID] = terminal_node

        for node in layer1.all:
            edge_tags_in = [edge.tag for edge in node.incoming]
            non_terminal_node = UccaNode(node.ID, edge_tags_in)
            ucca_parsed_passage.non_terminals.append(non_terminal_node)
            ucca_node_lookup[node.ID] = non_terminal_node

        # all the edges are from layer1 nodes to their children (which can include layer0
        # nodes)
        for node in layer1.all:
            for edge in node.outgoing:
                child_node = ucca_node_lookup[edge.child.ID]
                parent_node = ucca_node_lookup[edge.parent.ID]

                ucca_parsed_passage.edges.append(UccaEdge(child_node, parent_node, edge.tag))

        return ucca_parsed_passage
