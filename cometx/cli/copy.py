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
#  Copyright (c) 2023 Cometx Development
#      Team. All rights reserved.
# ****************************************
"""
To copy experiment data to new experiments.

cometx copy [--symlink] SOURCE DESTINATION

where SOURCE is:

* if not --symlink, "WORKSPACE/PROJECT/EXPERIMENT", "WORKSPACE/PROJECT", or "WORKSPACE" folder
* if --symlink, then it is a Comet path to workspace or workspace/project

where DESTINATION is:

* WORKSPACE
* WORKSPACE/PROJECT

Not all combinations are possible:


| Destination:       | WORKSPACE            | WORKSPACE/PROJECT      |
| Source (below)     |                      |                        |
|--------------------|----------------------|------------------------|
| WORKSPACE          | Copies all projects  | N/A                    |
| WORKSPACE/PROJ     | N/A                  | Copies all experiments |
| WORKSPACE/PROJ/EXP | N/A                  | Copies experiment      |
"""

import argparse
import glob
import json
import os
import sys

from comet_ml import API, APIExperiment, Experiment
from comet_ml.messages import (
    HtmlMessage,
    InstalledPackagesMessage,
    MetricMessage,
    StandardOutputMessage,
)

from ..utils import remove_extra_slashes

ADDITIONAL_ARGS = False


def get_parser_arguments(parser):
    parser.add_argument(
        "COMET_SOURCE",
        help=(
            "The folder containing the experiments to copy: 'workspace', or 'workspace/project' or 'workspace/project/experiment'"
        ),
        type=str,
    )
    parser.add_argument(
        "COMET_DESTINATION",
        help=("The Comet destination: 'WORKSPACE', 'WORKSPACE/PROJECT'"),
        type=str,
    )
    parser.add_argument(
        "--debug", help="If given, allow debugging", default=False, action="store_true"
    )
    parser.add_argument(
        "--symlink",
        help="Instead of copying, create a link to an experiment in a project",
        default=False,
        action="store_true",
    )


def copy(parsed_args, remaining=None):
    # Called via `cometx copy ...`
    try:
        copy_cli(parsed_args)
    except KeyboardInterrupt:
        print("Canceled by CONTROL+C")
    except Exception as exc:
        if parsed_args.debug:
            raise
        else:
            print("ERROR: " + str(exc))


def create_experiment(workspace_dst, project_dst):
    """
    Create an experiment in destination workspace
    and project, and return a APIExperiment.
    """
    experiment = Experiment(
        project_name=project_dst,
        workspace=workspace_dst,
        log_code=False,
        log_graph=False,
        auto_param_logging=False,
        auto_metric_logging=False,
        parse_args=False,
        auto_output_logging="simple",
        log_env_details=False,
        log_git_metadata=False,
        log_git_patch=False,
        disabled=False,
        log_env_gpu=False,
        log_env_host=False,
        display_summary=None,
        log_env_cpu=False,
        log_env_network=False,
        display_summary_level=1,
        optimizer_data=None,
        auto_weight_logging=None,
        auto_log_co2=False,
        auto_metric_step_rate=10,
        auto_histogram_tensorboard_logging=False,
        auto_histogram_epoch_rate=1,
        auto_histogram_weight_logging=False,
        auto_histogram_gradient_logging=False,
        auto_histogram_activation_logging=False,
        experiment_key=None,
    )
    return experiment


def get_experiment_folders(workspace_src, project_src, experiment_src):
    yield from glob.iglob(f"{workspace_src}/{project_src}/{experiment_src}")


def copy_experiment_to(experiment_folder, workspace_dst, project_dst):
    title = experiment_folder
    # See if there is a name:
    filename = os.path.join(experiment_folder, "others.jsonl")
    if os.path.isfile(filename):
        with open(filename) as fp:
            line = fp.readline()
            while line:
                others_json = json.loads(line)
                if others_json["name"] == "Name":
                    title = f"{experiment_folder} (\"{others_json['valueCurrent']}\")"
                    break
                line = fp.readline()
    print(f"Copying from {title} to {workspace_dst}/{project_dst}...")
    # if project doesn't exist, create it
    experiment = create_experiment(workspace_dst, project_dst)
    # copy experiment_folder stuff to experiment
    # copy all resources to existing or new experiment
    log_all(experiment, experiment_folder)
    experiment.end()
    print(f"    New experiment created: {experiment.url}")


def copy_cli(parsed_args):
    """
    | Destination:       | WORKSPACE            | WORKSPACE/PROJECT      |
    | Source (below)     |                      |                        |
    |--------------------|----------------------|------------------------|
    | WORKSPACE          | Copies all projects  | N/A                    |
    | WORKSPACE/PROJ     | N/A                  | Copies all experiments |
    | WORKSPACE/PROJ/EXP | N/A                  | Copies experiment      |
    """
    api = API()

    comet_destination = remove_extra_slashes(parsed_args.COMET_DESTINATION)
    comet_destination = comet_destination.split("/")
    if len(comet_destination) == 2:
        workspace_dst, project_dst = comet_destination
    elif len(comet_destination) == 1:
        workspace_dst = comet_destination[0]
        project_dst = None
    else:
        raise Exception("invalid COMET_DESTINATION: %r" % parsed_args.COMET_DESTINATION)

    comet_source = remove_extra_slashes(parsed_args.COMET_SOURCE)
    comet_source = comet_source.split("/")

    if len(comet_source) == 3:
        workspace_src, project_src, experiment_src = comet_source
    elif len(comet_source) == 2:
        workspace_src, project_src = comet_source
        experiment_src = "*"
    elif len(comet_source) == 1:
        workspace_src = comet_source[0]
        project_src, experiment_src = "*", "*"
    else:
        raise Exception("invalid COMET_SOURCE: %r" % parsed_args.COMET_SOURCE)

    # First check to make sure workspace_dst exists:
    workspaces = api.get_workspaces()
    if workspace_dst not in workspaces:
        raise Exception(
            f"{workspace_dst} does not exist; use the Comet UI to create it"
        )

    # For checking if the project_dst exists below:
    projects = api.get_projects(workspace_dst)

    for experiment_folder in get_experiment_folders(
        workspace_src, project_src, experiment_src
    ):
        _, folder_workspace, folder_project, folder_experiment = (
            "/" + experiment_folder
        ).rsplit("/", 3)
        if folder_experiment in ["project_metadata.json"]:
            continue
        
        temp_project_dst = project_dst
        if temp_project_dst is None:
            temp_project_dst = folder_project

        # Next, check if the project_dst exists:
        if temp_project_dst not in projects:
            project_metadata_path = os.path.join(workspace_src, project_src, "project_metadata.json")
            if os.path.exists(project_metadata_path):
                with open(project_metadata_path) as fp:
                    project_metadata = json.load(fp)
                api.create_project(
                    workspace_dst,
                    temp_project_dst,
                    project_description=project_metadata["projectDescription"],
                    public=project_metadata["public"]
                )
            projects.append(temp_project_dst)

        if parsed_args.symlink:
            print(
                f"Creating symlink from {workspace_src}/{project_src}/{experiment_src} to {workspace_dst}/{temp_project_dst}"
            )
            experiment = APIExperiment(previous_experiment=experiment_src)
            experiment.create_symlink(temp_project_dst)
            print(
                f"    New symlink created: {api._get_url_server()}/{workspace_dst}/{temp_project_dst}/{experiment_src}"
            )
        else:
            copy_experiment_to(experiment_folder, workspace_dst, temp_project_dst)

    return


def log_metadata(experiment, filename):
    # FIXME
    # filename
    if os.path.exists(filename):
        metadata = json.load(open(filename))
        experiment.add_tags(metadata["tags"])
        # FIXME: missing:
        #  throttle data
        #  durationMillis
        #  startTimeMillis
        #  endTimeMillis


def log_graph(experiment, filename):
    if os.path.exists(filename):
        experiment.set_model_graph(open(filename).read())


def log_assets(experiment, path, assets_metadata):
    """
    {"fileName": "text-sample-3.txt",
     "fileSize": 37,
     "runContext": null,
     "step": 3,
     "remote": false,
     "link": "",
     "compressedAssetLink": "",
     "s3Link": "",
     "createdAt": 1694757164606,
     "dir": "text-samples",
     "canView": false,
     "audio": false,
     "video": false,
     "histogram": false,
     "image": false,
     "type": "text-sample",
     "metadata": null,
     "assetId": "0f8faff37fda4d40b7e0f5c665c3611a",
     "tags": [],
     "curlDownload": "",
     "experimentKey": "92ecd97e311c41939c7f68ddec98ba67"
    }
    """
    for log_filename in assets_metadata:
        asset_type = assets_metadata[log_filename].get("type", None)
        asset_type = asset_type if asset_type else "asset"
        if log_filename.startswith("/"):
            filename = os.path.join(path, asset_type, log_filename[1:])
        else:
            filename = os.path.join(path, asset_type, log_filename)

        if not os.path.isfile(filename):
            print("Missing file %r: unable to copy" % filename)
            continue

        metadata = assets_metadata[log_filename].get("metadata")
        metadata = json.loads(metadata) if metadata else {}

        if asset_type == "notebook":
            experiment.log_notebook(filename)  # done!
            # elif asset_type == "confusion-matrix":
            # TODO: what to do about assets referenced in matrix?
            # elif asset_type == "embedding":
            # TODO: what to do about assets referenced in embedding?
        else:
            binary_io = open(filename, "rb")

            experiment._log_asset(
                binary_io,
                file_name=log_filename,
                copy_to_tmp=True,
                asset_type=asset_type,
                metadata=metadata,
                step=assets_metadata[log_filename].get("step", None),
            )  # done!


def log_code(experiment, filename):
    """ """
    if os.path.exists(filename):
        if os.path.isfile(filename):
            experiment.log_code(str(filename))
        elif os.path.isdir(filename):
            experiment.log_code(folder=str(filename))


def log_requirements(experiment, filename):
    """
    Requirements (pip packages)
    """
    if os.path.exists(filename):
        installed_packages_list = [package.strip() for package in open(filename)]
        if installed_packages_list is None:
            return
        message = InstalledPackagesMessage.create(
            context=experiment.context,
            use_http_messages=experiment.streamer.use_http_messages,
            installed_packages=installed_packages_list,
        )
        experiment._enqueue_message(message)


def log_metrics(experiment, filename):
    """ """
    if os.path.exists(filename):
        for line in open(filename):
            dict_line = json.loads(line)
            name = dict_line["metricName"]
            value = dict_line["metricValue"]
            step = dict_line["step"]
            epoch = dict_line["epoch"]
            context = dict_line["runContext"]
            timestamp = dict_line["timestamp"]
            # FIXME: does not log time, duration
            message = MetricMessage.create(
                context=context,
                use_http_messages=experiment.streamer.use_http_messages,
                timestamp=timestamp,
            )
            message.set_metric(name, value, step=step, epoch=epoch)
            experiment._enqueue_message(message)


def log_parameters(experiment, filename):
    """ """
    if os.path.exists(filename):
        parameters = json.load(open(filename))
        for parameter in parameters:
            name = parameter["name"]
            value = parameter["valueCurrent"]
            experiment.log_parameter(name, value)


def log_others(experiment, filename):
    """ """
    if os.path.exists(filename):
        for line in open(filename):
            dict_line = json.loads(line)
            name = dict_line["name"]
            value = dict_line["valueCurrent"]
            experiment.log_other(key=name, value=value)


def log_output(experiment, output_file):
    """ """
    if os.path.exists(output_file):
        for line in open(output_file):
            message = StandardOutputMessage.create(
                context=experiment.context,
                use_http_messages=experiment.streamer.use_http_messages,
                output=line,
                stderr=False,
            )
            experiment._enqueue_message(message)


def log_html(experiment, filename):
    if os.path.exists(filename):
        html = open(filename).read()
        message = HtmlMessage.create(
            context=experiment.context,
            use_http_messages=experiment.streamer.use_http_messages,
            html=html,
        )
        experiment._enqueue_message(message)


def log_all(experiment, experiment_folder):
    """ """
    # FIXME: missing notes (edited by human, not logged programmatically)
    log_metrics(experiment, os.path.join(experiment_folder, "metrics.jsonl"))

    log_metadata(experiment, os.path.join(experiment_folder, "metadata.json"))

    log_parameters(experiment, os.path.join(experiment_folder, "parameters.json"))

    log_others(experiment, os.path.join(experiment_folder, "others.jsonl"))

    assets_metadata_filename = os.path.join(
        experiment_folder, "assets", "assets_metadata.jsonl"
    )
    assets_metadata = {}
    if os.path.exists(assets_metadata_filename):
        for line in open(assets_metadata_filename):
            data = json.loads(line)
            assets_metadata[data["fileName"]] = data

        log_assets(
            experiment, os.path.join(experiment_folder, "assets"), assets_metadata
        )

    log_output(experiment, os.path.join(experiment_folder, "run/output.txt"))

    log_requirements(
        experiment, os.path.join(experiment_folder, "run/requirements.txt")
    )

    log_graph(experiment, os.path.join(experiment_folder, "run/graph_definition.txt"))

    log_html(
        experiment,
        os.path.join(experiment_folder, "experiment.html"),
    )

    # FIXME:
    ## models


def main(args):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    get_parser_arguments(parser)
    parsed_args = parser.parse_args(args)
    copy(parsed_args)


if __name__ == "__main__":
    # Called via `python -m cometx.cli.copy ...`
    main(sys.argv[1:])
