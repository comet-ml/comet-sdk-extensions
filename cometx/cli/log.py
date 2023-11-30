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

To log to an experiment or set other key:value to multiple experiments:


$ cometx log WORKSPACE/PROJECT FOLDER --type=all
$ cometx log WORKSPACE/PROJECT/EXPERIMENT-KEY FILENAME --type=TYPE
$ cometx log WORKSPACE/PROJECT --type=other --set "key:value"
$ cometx log WORKSPACE --type=other --set "key:value"

Where TYPE is one of the following names:

* all
* asset
* audio
* code
* image
* metrics
* notebook
* text-sample
* video
* other
"""
import argparse
import glob
import json
import os
import sys

from comet_ml import API

from ..utils import get_file_extension, get_query_experiments

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
    parser.add_argument(
        "--set",
        help="The key:value to log",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--query",
        help="A Comet Query string, see https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/API/#apiquery",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--debug", help="If given, allow debugging", default=False, action="store_true"
    )


def log(parsed_args, remaining=None):
    # Called via `cometx log ...`
    try:
        log_cli(parsed_args)
    except KeyboardInterrupt:
        print("Canceled by CONTROL+C")
    except Exception as exc:
        if parsed_args.debug:
            raise
        else:
            print("ERROR: " + str(exc))


def log_cli(parsed_args):
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

    api = API()

    if experiment_key:
        experiments = [api.get_experiment_by_key(experiment_key)]
    elif parsed_args.query is not None:
        experiments = get_query_experiments(
            api, parsed_args.query, workspace, project_name
        )
    else:
        experiments = api.get_experiments(workspace, project_name)

    if parsed_args.type == "all":
        if not parsed_args.FILENAME:
            raise Exception("Logging `all` requires a folder")

        for experiment in experiments:
            if os.path.exists(os.path.join(parsed_args.FILENAME, "metrics.jsonl")):
                log_experiment_metrics_from_file(
                    experiment, os.path.join(parsed_args.FILENAME, "metrics.jsonl")
                )

            if os.path.exists(os.path.join(parsed_args.FILENAME, "parameters.json")):
                log_experiment_parameters_from_file(
                    experiment, os.path.join(parsed_args.FILENAME, "parameters.json")
                )

            if os.path.exists(os.path.join(parsed_args.FILENAME, "others.jsonl")):
                log_experiment_others_from_file(
                    experiment, os.path.join(parsed_args.FILENAME, "others.jsonl")
                )

            for dirname in glob.glob(os.path.join(parsed_args.FILENAME, "assets", "*")):
                if os.path.isdir(dirname):
                    base, asset_type = dirname.rsplit("/", 1)
                    log_experiment_assets_from_file(
                        experiment,
                        os.path.join(parsed_args.FILENAME, "assets", asset_type, "*"),
                        asset_type,
                    )

        # FIXME: output

    elif parsed_args.type == "code":
        if not parsed_args.FILENAME:
            raise Exception("Logging `code` requires a file or folder")

        for experiment in experiments:
            log_experiment_code_from_file(experiment, parsed_args.FILENAME)

    elif parsed_args.type == "other":
        # two possibilities: log key:value to set of experiments; log filename to experiment
        if parsed_args.FILENAME:
            for experiment in experiments:
                log_experiment_others_from_file(experiment, parsed_args.FILENAME)
            return

        elif not parsed_args.set or ":" not in parsed_args.set:
            raise Exception("Logging `other` without FILENAME requires --set key:value")

        key, value = parsed_args.set.split(":", 1)
        set_experiments_other(experiments, key, value)

    elif parsed_args.type == "metrics":
        if not parsed_args.FILENAME:
            raise Exception("Logging `metrics` requires a file")

        for experiment in experiments:
            log_experiment_metrics_from_file(experiment, parsed_args.FILENAME)

    elif parsed_args.type == "parameters":
        if not parsed_args.FILENAME:
            raise Exception("Logging `parameters` requires a file")

        for experiment in experiments:
            log_experiment_parameters_from_file(experiment, parsed_args.FILENAME)

    else:
        if not parsed_args.FILENAME:
            raise Exception("Logging an asset requires a file")

        for experiment in experiments:
            log_experiment_assets_from_file(
                experiment, parsed_args.FILENAME, parsed_args.type
            )

    if experiment:
        experiment.end()


def log_experiment_assets_from_file(experiment, filename, file_type):
    SKELETON = filename
    for filename in glob.glob(SKELETON):
        if not file_type:
            extension = get_file_extension(filename)
            file_type = EXTENSION_MAP.get(extension.lower(), "asset")

        # metadata = FIXME: get metadata dict from args
        experiment.log_asset(
            filename,
            ftype=file_type,
        )


def log_experiment_code_from_file(experiment, filename):
    if os.path.isfile(filename):
        experiment.log_code(filename)
    elif os.path.isdir(filename):
        experiment.log_code(folder=filename)
    else:
        raise Exception("cannot log code: %r; use filename or folder" % filename)


def set_experiments_other(experiments, key, value):
    from ..generate_utils import generate_experiment_name

    for count, experiment in enumerate(experiments):
        new_value = value.replace("{random}", generate_experiment_name())
        new_value = value.replace("{count}", str(count + 1))
        experiment.log_other(key, new_value)


def log_experiment_metrics_from_file(experiment, filename):
    for line in open(filename):
        dict_line = json.loads(line)
        name = dict_line["metricName"]
        value = dict_line["metricValue"]
        step = dict_line["step"]
        epoch = dict_line["epoch"]
        # FIXME: does not log time
        experiment.log_metric(name=name, value=value, step=step, epoch=epoch)


def log_experiment_parameters_from_file(experiment, filename):
    parameters = json.load(open(filename))
    for parameter in parameters:
        name = parameter["name"]
        value = parameter["valueCurrent"]
        experiment.log_parameter(name, value)


def log_experiment_others_from_file(experiment, filename):
    for line in open(filename):
        dict_line = json.loads(line)
        name = dict_line["name"]
        value = dict_line["valueCurrent"]
        experiment.log_other(key=name, value=value)


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
