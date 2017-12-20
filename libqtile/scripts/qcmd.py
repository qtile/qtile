#!/usr/bin/env python
from __future__ import print_function
import pprint
import argparse
from libqtile.command import Client
from libqtile.command import CommandError, CommandException


def get_formated_info(obj, cmd, args=True, short=True):
    doc_func = obj.doc if hasattr(obj, "doc") else lambda x: ""
    doc = doc_func(cmd).splitlines()

    if doc:
        short_description = doc[1] if len(doc) > 1 else ""

        tdoc = doc[0]
        doc_args = tdoc[tdoc.find("(")+1:tdoc.find(")")].strip()

        if doc_args:  # return formatted args
            doc_args = "({})".format(doc_args)

    if args is False:
        doc_args = ""
    elif args and short:
        doc_args = "*" if len(doc_args) > 1 else " "

    return (doc_args + " " + short_description).rstrip()

def print_commands(prefix, obj):
    prefix += " -f "
    output = []
    max_cmd = 0  # max len of cmd for formatting

    try:
        cmds = obj.commands()
    except:
        print("error: Sorry no commands in ", prefix)
        exit()

    for cmd in cmds:
        doc_args = get_formated_info(obj, cmd)

        pcmd = prefix + cmd
        max_cmd = max(len(pcmd), max_cmd)
        output.append([pcmd, doc_args])

    # Print formatted output
    formating = "{:<%d}\t{}" % (max_cmd + 1)
    for line in output:
        print(formating.format(line[0], line[1]))


def get_object(argv):

    client = Client()

    if argv[0] == "cmd":
        obj = client
    else:
        obj = getattr(client, argv[0])

    # Generate full obj specification
    for arg in argv[1:]:
        try:
            obj = obj[arg]  # check if it is an item
        except Exception:
            try:
                obj = getattr(obj, arg)  # check it it is an attr
            except Exception:
                print("Specified object does not exist" + " ".join(argv))
                exit()

    return obj


def run_function(obj, funcname, args):
    func = getattr(obj, funcname)

    try:
        ret = func(*args)
    except CommandError:
        print("error: Sorry command '{}' cannot be found".format(funcname))
        exit()
    except CommandException:
        print("error: Sorry cannot run function '{}' with arguments {}"
              .format(funcname, args))
        exit()

    return ret


def print_base_objects():
    actions = ["-o cmd", "-o window", "-o layout", "-o group"]
    print("\n".join(actions))


def main():
    description = 'Simple tool to expose qtile.command functionality to shell.'
    epilog = '''\
Examples:\n\
 qcmd\n\
 qcmd -o cmd\n\
 qcmd -o cmd -f prev_layout -i\n\
 qcmd -o cmd -f prev_layout -a 3 # prev_layout on group 3\n\
 qcmd -o group 3 -f focus_back\n
'''
    fmt = argparse.RawDescriptionHelpFormatter

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=fmt)
    parser.add_argument('--object', '-o', dest='obj_spec', nargs='+',
                        help='''Specify path to object (space separated).\
                        If no --function flag display available commands.''')
    parser.add_argument('--function', '-f', dest='function', nargs=1,
                        default="help", help='Select function to execute.')
    parser.add_argument('--args', '-a', dest='args', nargs='+',
                        default=[], help='Set arguments supplied to function.')
    parser.add_argument('--info', '-i', dest='info', action='store_true',
                        help='''With both --object and --function args prints\
                        documentation for function.''')
    args = parser.parse_args()

    if args.obj_spec:

        obj = get_object(args.obj_spec)

        if args.function == "help":
            print_commands("-o " + " ".join(args.obj_spec), obj)
        elif args.info:
            print(get_formated_info(obj, args.function[0],
                                    args=True, short=False))
        else:
            ret = run_function(obj, args.function[0], args.args)
            if ret is not None:
                pprint.pprint(ret)
            else:
                print_commands("-o " + " ".join(args.obj_spec), obj)

    else:
        print_base_objects()


if __name__ == "__main__":
    main()
