import argparse
import gc
import pdb
import sys
from lib import Strip

parser = argparse.ArgumentParser(description='Analyze the reachable states in a Verilog netlist')
parser.add_argument('--design', help='Top-level module', required=True)
parser.add_argument('--inputs', nargs='*', default=[], help='list of input-constraint files')
parser.add_argument('--design-dir', default='designs.protocol', help='Design directory')
parser.add_argument('--dump-groups', help='Dump all groups found, exit')
parser.add_argument('--read-groups', help='Read all groups from user file')
parser.add_argument('--max-states', type=int, default=21, help='Maximum reachable states tolerated in a group (log2)')
parser.add_argument('--window-size', type=int, default=14, help='Sliding-window size (w)')
parser.add_argument('--window-step', type=int, default=8, help='Sliding-window step (s)')
parser.add_argument('--protocol-fifo', default='fifo_capacity_', help='Instance names of protocol FIFOs')
parser.add_argument('--verbose', '-v', action='count', help='verbosity level')
parser.add_argument('--version', action='version', version='%(prog)s 1.0')
args = parser.parse_args()


print vars(args)
fs = Strip.Strip(vars(args))
gc.disable()
fs.run()
fs.printTime()
fs.printGroups()
gc.enable()
