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
import glob
import json
import os
import sys

from comet_ml import ExistingExperiment, Experiment

from ..utils import get_file_extension

ADDITIONAL_ARGS = False
# From filename extension to Comet Asset Type
EXTENSION_MAP = {
    "asset": "asset",
    "datagrid": "datagrid",
    "png": "image",
    "jpg": "image",
    "gif": "image",
    "txt": "text-sample",
    "webm": "video",
    "mp4": "video",
    "ogg": "video",
    "ipynb": "notebook",
    "wav": "audio",
    "mp3": "audio",
    #    "curve": "curve", FIXME: add
}
# Fom CLI type to Comet Asset Type
# List only those that differ from
# type.lower() != Comet Asset Type
TYPE_MAP = {
    "text": "text-sample",
}


def get_parser_arguments(parser):
    parser.add_argument(
        "COMET_PATH",
        help=(
            "The Comet identifier, such as 'WORKSPACE', 'WORKSPACE/PROJECT', or "
            + "'WORKSPACE/PROJECT/EXPERIMENT'. Leave empty to use defaults."
        ),
        nargs="?",
        default=None,
        type=str,
    )
    parser.add_argument(
        "FILENAME",
        help=("The filename or directory to log"),
        nargs="?",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--type",
        help="The type of item to log",
        type=str,
        default=None,
    )


def log(parsed_args, remaining=None):
    # Called via `cometx log ...`
    try:
        log_cli(parsed_args)
    except KeyboardInterrupt:
        print("Canceled by CONTROL+C")
    except Exception as exc:
        print("ERROR: " + str(exc))


def log_cli(parsed_args):
    if parsed_args.type:
        log_type = TYPE_MAP.get(parsed_args.type.lower(), parsed_args.type.lower())
    else:
        extension = get_file_extension(parsed_args.FILENAME)
        log_type = EXTENSION_MAP.get(extension.lower(), "asset")

    if parsed_args.FILENAME is None:
        parsed_args.FILENAME, parsed_args.COMET_PATH = (
            parsed_args.COMET_PATH,
            parsed_args.FILENAME,
        )

    if parsed_args.FILENAME is None:
        raise Exception("Provide a filename to log to experiment")

    comet_path = (
        parsed_args.COMET_PATH.split("/") if parsed_args.COMET_PATH is not None else []
    )

    if not comet_path:
        workspace = None
        project_name = None
        experiment_key = None
    elif len(comet_path) == 1:
        workspace = comet_path[0]
        project_name = None
        experiment_key = None
    elif len(comet_path) == 2:
        workspace, project_name = comet_path
        experiment_key = None
    elif len(comet_path) == 3:
        workspace, project_name, experiment_key = comet_path
    else:
        raise Exception("invalid COMET_PATH: %r" % parsed_args.COMET_PATH)

    if experiment_key:
        experiment = ExistingExperiment(
            previous_experiment=experiment_key,
            workspace=workspace,
            project_name=project_name,
        )
    else:
        experiment = Experiment(
            workspace=workspace,
            project_name=project_name,
        )

    # Try as glob:
    if parsed_args.type == "code":
        if os.path.isfile(parsed_args.FILENAME):
            experiment.log_code(file_name=parsed_args.FILENAME)
        elif os.path.isdir(parsed_args.FILENAME):
            experiment.log_code(folder=parsed_args.FILENAME)
        else:
            raise Exception("cannot log code: %r; use filename or folder")
    elif parsed_args.type == "metrics":
        for line in open(parsed_args.FILENAME):
            dict_line = json.loads(line)
            name = dict_line["metricName"]
            value = dict_line["metricValue"]
            step = dict_line["step"]
            epoch = dict_line["epoch"]
            # FIXME: does not log time
            experiment.log_metric(name=name, value=value, step=step, epoch=epoch)
    else:
        SKELETON = parsed_args.FILENAME
        for filename in glob.glob(SKELETON):
            comet_log_type = TYPE_MAP.get(log_type, log_type)
            if comet_log_type in ["image", "text-sample", "asset", "video", "audio"]:
                # metadata = FIXME: get metadata dict from args
                binary_io = open(filename, "rb")

                experiment._log_asset(
                    binary_io,
                    file_name=filename,
                    copy_to_tmp=True,  # NOTE: comet_ml no longer support False
                    asset_type=comet_log_type,
                )
            elif comet_log_type == "notebook":
                # metadata = FIXME: get metadata dict from args
                experiment.log_notebook(filename)
            else:
                raise print("ERROR: Unable to log type: %r" % parsed_args.type)

    experiment.end()


def main(args):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    get_parser_arguments(parser)
    parsed_args = parser.parse_args(args)
    log(parsed_args)


if __name__ == "__main__":
    # Called via `python -m cometx.cli.log ...`
    main(sys.argv[1:])
