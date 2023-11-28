#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************
#                              __
#   _________  ____ ___  ___  / /__  __
#  / ___/ __ \/ __ `__ \/ _ \/ __/ |/_/
# / /__/ /_/ / / / / / /  __/ /__>  <
# \___/\____/_/ /_/ /_/\___/\__/_/|_|
#
#
#  Copyright (c) 2022 Cometx Development
#      Team. All rights reserved.
# ****************************************
"""
Examples:

    cometx download
    cometx copy
    cometx log
    cometx list
    cometx reproduce
    cometx delete

For more information:
    cometx COMMAND --help
"""
import argparse
import sys

from cometx import __version__

# Import CLI commands:
from . import copy, delete, download, list_command, log, reproduce


def add_subparser(subparsers, module, name):
    """
    Loads scripts and creates subparser.

    Assumes: NAME works for:
       * NAME.NAME is the function
       * comet_NAME.ADDITIONAL_ARGS is set to True/False
       * comet_NAME.get_parser_arguments is defined
    """
    func = getattr(module, name)
    additional_args = module.ADDITIONAL_ARGS
    get_parser_arguments = module.get_parser_arguments
    docs = module.__doc__

    parser = subparsers.add_parser(
        name, description=docs, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.set_defaults(func=func)
    parser.set_defaults(additional_args=additional_args)
    get_parser_arguments(parser)


def main(raw_args=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--version",
        help="Display comet_ml version",
        action="store_const",
        const=True,
        default=False,
    )
    subparsers = parser.add_subparsers()

    # Register CLI commands:
    add_subparser(subparsers, download, "download")
    add_subparser(subparsers, copy, "copy")
    add_subparser(subparsers, log, "log")
    add_subparser(subparsers, delete, "delete")
    add_subparser(subparsers, list_command, "list")
    add_subparser(subparsers, reproduce, "reproduce")

    # First identify the subparser as some subparser pass additional args to
    # the subparser and other not

    args, rest = parser.parse_known_args(raw_args)

    # args won't have additional args if no subparser added
    if hasattr(args, "additional_args") and args.additional_args:
        parser_func = args.func

        parser_func(args, rest)
    elif args.version:
        print(__version__)
    else:
        # If the subcommand doesn't need extra args, reparse in strict mode so
        # the users get a nice message in case of unsupported CLi argument
        args = parser.parse_args(raw_args)
        if hasattr(args, "func"):
            parser_func = args.func

            parser_func(args)
        else:
            # comet with no args; call recursively:
            main(["--help"])


if __name__ == "__main__":
    main(sys.argv[1:])
