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

import argparse
import sys
import os

from comet_ml.exceptions import InvalidRestAPIKey
from comet_ml.utils import makedirs

from cometx.download_manager import DownloadManager, clean_comet_path
from cometx.utils import display_invalid_api_key

ADDITIONAL_ARGS = False


def get_parser_arguments(parser):
    parser.add_argument(
        "COMET_PATH",
        help=(
            "The Comet identifier, such as 'WORKSPACE', 'WORKSPACE/PROJECT', or "
            + "'WORKSPACE/PROJECT/EXPERIMENT'. Leave empty for all workspaces."
        ),
        type=str,
    )
    parser.add_argument(
        "OUTPUT_DIR",
        help=(
            "The directory to copy files in order to reproduce the experiment"
        ),
        type=str,
    )
    parser.add_argument(
        "--run",
        help=(
            "Run the reproducable script"
        ),
        action="store_true",
        default=False,
    )

def reproduce(parsed_args, remaining=None):
    comet_path = (
        parsed_args.COMET_PATH.split("/") if parsed_args.COMET_PATH is not None else []
    )

    if len(comet_path) != 3:
        raise Exception("invalid COMET_PATH: %r; requires workspace/project/experiment" % parsed_args.COMET_PATH)
    else:
        comet_path = clean_comet_path("/".join(comet_path))

    manager = DownloadManager()
    manager.root = parsed_args.OUTPUT_DIR
    manager.use_name = False
    manager.flat = True
    manager.force = False
    manager.filename = None
    manager.overwrite = True
    manager.summary = {key: 0 for key in manager.RESOURCE_FUNCTIONS.keys()}
    manager.summary["artifacts"] = 0
    manager.summary["model-registry"] = 0
        
    experiment = manager.api.get(comet_path)
    if experiment is None:
        raise Exception("invalid experiment: %r; not found, or not available" % comet_path)

    makedirs(parsed_args.OUTPUT_DIR, exist_ok=True)
    manager.download_code(experiment)
    manager.download_git(experiment)
    manager.download_requirements(experiment)

    shell_commands = "cd %s" % parsed_args.OUTPUT_DIR
    shell_commands += manager.get_git_text(experiment)
    shell_commands += "python ../script.py"

    shell_script_name = os.path.join(parsed_args.OUTPUT_DIR, "script.sh")
    with open(shell_script_name, "w") as fp:
        fp.write(shell_commands)

    os.system("chmod +x %s" % shell_script_name)

    print("Shell command saved in: %s" % shell_script_name)
    if parsed_args.run:
        print("Running...")
        os.system("%s" % shell_script_name)
    else:
        print("To run simply execute the script.")


def main(args):
    # Called via `cometx reproduce ...`
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    get_parser_arguments(parser)
    parsed_args = parser.parse_args(args)

    reproduce(parsed_args)


if __name__ == "__main__":
    # Called via `python -m cometx.cli.reproduce ...`
    # Called via `cometx reproduce ...`
    main(sys.argv[1:])
