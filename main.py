#!/usr/bin/env python3

from src.Osintgram import Osintgram
import argparse
from src import printcolors as pc
from src import artwork
import sys
import signal

is_windows = False

try:
    import gnureadline  
except: 
    is_windows = True
    import pyreadline


def printlogo():
    pc.printout(artwork.ascii_art, pc.BLUE)
    pc.printout("\nVersion 1.1 - Developed by Giuseppe Criscione | Updated by Lesmana.\n\n", pc.BLUE)
    pc.printout("\n\n\n")
    pc.printout("Command List.\n", pc.BLUE)
    pc.printout("1\t")
    print("Get followers data")
    pc.printout("2\t")
    print("Get followings data")
    pc.printout("3\t")
    print("Get detail data of target followers")
    pc.printout("4\t")
    print("Get detail data target followings")
    pc.printout("target\t")
    print("Change target")


def cmdlist():
    pc.printout("1\t")
    print("Get followers data")
    pc.printout("2\t")
    print("Get followings data")
    pc.printout("3\t")
    print("Get detail data of target followers")
    pc.printout("4\t")
    print("Get detail data target followings")
    pc.printout("target\t")
    print("Change target")


def signal_handler(sig, frame):
    pc.printout("\nGoodbye!\n", pc.RED)
    sys.exit(0)


def completer(text, state):
    options = [i for i in commands if i.startswith(text)]
    if state < len(options):
        return options[state]
    else:
        return None

def _quit():
    pc.printout("Goodbye!\n", pc.RED)
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
if is_windows:
    pyreadline.Readline().parse_and_bind("tab: complete")
    pyreadline.Readline().set_completer(completer)
else:
    gnureadline.parse_and_bind("tab: complete")
    gnureadline.set_completer(completer)

parser = argparse.ArgumentParser(description='Osintgram is a OSINT tool on Instagram. It offers an interactive shell '
                                             'to perform analysis on Instagram account of any users by its nickname ')
parser.add_argument('id', type=str,  # var = id
                    help='username')
parser.add_argument('-C','--cookies', help='clear\'s previous cookies', action="store_true")
parser.add_argument('-j', '--json', help='save commands output as JSON file', action='store_true')
parser.add_argument('-f', '--file', help='save output in a file', action='store_true')
parser.add_argument('-c', '--command', help='run in single command mode & execute provided command', action='store')
parser.add_argument('-o', '--output', help='where to store photos', action='store')

args = parser.parse_args()


api = Osintgram(args.id, args.file, args.json, args.command, args.output, args.cookies)



commands = {
    'list':             cmdlist,
    'help':             cmdlist,
    'quit':             _quit,
    'exit':             _quit,
    '1':            api.get_followers,
    '2':            api.get_followings,
    '3':            api.get_detail_followers,
    '4':            api.get_detail_followings,
    'target':       api.change_target,
}


signal.signal(signal.SIGINT, signal_handler)
if is_windows:
    pyreadline.Readline().parse_and_bind("tab: complete")
    pyreadline.Readline().set_completer(completer)
else:
    gnureadline.parse_and_bind("tab: complete")
    gnureadline.set_completer(completer)

if not args.command:
    printlogo()


while True:
    if args.command:
        cmd = args.command
        _cmd = commands.get(args.command)
    else:
        signal.signal(signal.SIGINT, signal_handler)
        if is_windows:
            pyreadline.Readline().parse_and_bind("tab: complete")
            pyreadline.Readline().set_completer(completer)
        else:
            gnureadline.parse_and_bind("tab: complete")
            gnureadline.set_completer(completer)
        pc.printout("Run a command: ", pc.YELLOW)
        cmd = input()

        _cmd = commands.get(cmd)

    if _cmd:
        _cmd()
    elif cmd == "FILE=y":
        api.set_write_file(True)
    elif cmd == "FILE=n":
        api.set_write_file(False)
    elif cmd == "JSON=y":
        api.set_json_dump(True)
    elif cmd == "JSON=n":
        api.set_json_dump(False)
    elif cmd == "":
        print("")
    else:
        pc.printout("Unknown command\n", pc.RED)

    if args.command:
        break
