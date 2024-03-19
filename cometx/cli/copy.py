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

from comet_ml import API, APIExperiment, Artifact, Experiment, OfflineExperiment
from comet_ml._typing import TemporaryFilePath
from comet_ml.connection import compress_git_patch
from comet_ml.file_uploader import GitPatchUploadProcessor
from comet_ml.messages import (
    GitMetadataMessage,
    HtmlMessage,
    InstalledPackagesMessage,
    MetricMessage,
    StandardOutputMessage,
    SystemDetailsMessage,
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
        "-i",
        "--ignore",
        help="Resource(s) (or 'experiments') to ignore.",
        nargs="+",
        default=[],
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
        copy_manager = CopyManager()
        copy_manager.copy(
            parsed_args.COMET_SOURCE,
            parsed_args.COMET_DESTINATION,
            parsed_args.symlink,
            parsed_args.ignore,
        )
        if parsed_args.debug:
            print("finishing...")

    except KeyboardInterrupt:
        if parsed_args.debug:
            raise
        else:
            print("Canceled by CONTROL+C")
    except Exception as exc:
        if parsed_args.debug:
            raise
        else:
            print("ERROR: " + str(exc))


class CopyManager:
    def __init__(self):
        """
        | Destination:       | WORKSPACE            | WORKSPACE/PROJECT      |
        | Source (below)     |                      |                        |
        |--------------------|----------------------|------------------------|
        | WORKSPACE          | Copies all projects  | N/A                    |
        | WORKSPACE/PROJ     | N/A                  | Copies all experiments |
        | WORKSPACE/PROJ/EXP | N/A                  | Copies experiment      |
        """
        self.api = API()

    def copy(self, source, destination, symlink, ignore):
        """ """
        self.ignore = ignore
        self.debug = True
        self.copied_reports = False
        comet_destination = remove_extra_slashes(destination)
        comet_destination = comet_destination.split("/")
        if len(comet_destination) == 2:
            workspace_dst, project_dst = comet_destination
        elif len(comet_destination) == 1:
            workspace_dst = comet_destination[0]
            project_dst = None
        else:
            raise Exception("invalid COMET_DESTINATION: %r" % destination)

        comet_source = remove_extra_slashes(source)
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
            raise Exception("invalid COMET_SOURCE: %r" % source)

        # First check to make sure workspace_dst exists:
        workspaces = self.api.get_workspaces()
        if workspace_dst not in workspaces:
            raise Exception(
                f"{workspace_dst} does not exist; use the Comet UI to create it"
            )

        # For checking if the project_dst exists below:
        projects = self.api.get_projects(workspace_dst)

        for experiment_folder in self.get_experiment_folders(
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
                project_metadata_path = os.path.join(
                    workspace_src, project_src, "project_metadata.json"
                )
                if os.path.exists(project_metadata_path):
                    with open(project_metadata_path) as fp:
                        project_metadata = json.load(fp)
                    self.api.create_project(
                        workspace_dst,
                        temp_project_dst,
                        project_description=project_metadata["projectDescription"],
                        public=project_metadata["public"],
                    )
                projects.append(temp_project_dst)

            if symlink:
                print(
                    f"Creating symlink from {workspace_src}/{project_src}/{experiment_src} to {workspace_dst}/{temp_project_dst}"
                )
                experiment = APIExperiment(previous_experiment=experiment_src)
                experiment.create_symlink(temp_project_dst)
                print(
                    f"    New symlink created: {self.api._get_url_server()}/{workspace_dst}/{temp_project_dst}/{experiment_src}"
                )
            elif "experiments" not in self.ignore:
                self.copy_experiment_to(
                    experiment_folder, workspace_dst, temp_project_dst
                )

    def create_experiment(self, workspace_dst, project_dst, offline=True):
        """
        Create an experiment in destination workspace
        and project, and return an Experiment.
        """
        if self.debug:
            print("Creating experiment...")

        ExperimentClass = OfflineExperiment if offline else Experiment
        experiment = ExperimentClass(
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

    def get_experiment_folders(self, workspace_src, project_src, experiment_src):
        for path in glob.iglob(f"{workspace_src}/{project_src}/{experiment_src}"):
            if any(
                [path.endswith("~"), path.endswith(".json"), path.endswith(".jsonl")]
            ):
                continue
            else:
                yield path

    def copy_experiment_to(self, experiment_folder, workspace_dst, project_dst):
        title = experiment_folder
        # See if there is a name:
        filename = os.path.join(experiment_folder, "others.jsonl")
        if os.path.isfile(filename):
            with open(filename) as fp:
                line = fp.readline()
                while line:
                    others_json = json.loads(line)
                    if others_json["name"] == "Name":
                        title = (
                            f"{experiment_folder} (\"{others_json['valueCurrent']}\")"
                        )
                        break
                    line = fp.readline()
        print(f"Copying from {title} to {workspace_dst}/{project_dst}...")

        # Copy other project-level items to an experiment:
        if "reports" not in self.ignore and not self.copied_reports:
            experiment = None
            workspace_src, project_src, _ = experiment_folder.split("/")
            reports = os.path.join(workspace_src, project_src, "reports", "*")
            for filename in glob.glob(reports):
                if filename.endswith("reports_metadata.jsonl"):
                    continue
                basename = os.path.basename(filename)
                artifact = Artifact(basename, "Report")
                artifact.add(filename)
                if experiment is None:
                    experiment = self.create_experiment(
                        workspace_dst, project_dst, offline=False
                    )
                    experiment.log_other("Name", "Reports")
                experiment.log_artifact(artifact)
            if experiment:
                experiment.end()
            self.copied_reports = True

        # if project doesn't exist, create it
        experiment = self.create_experiment(workspace_dst, project_dst)

        # copy experiment_folder stuff to experiment
        # copy all resources to existing or new experiment
        self.log_all(experiment, experiment_folder)
        experiment.end()
        print(
            f"Uploading {experiment.offline_directory}/{experiment._get_offline_archive_file_name()}"
        )
        os.system(
            f"comet upload {experiment.offline_directory}/{experiment._get_offline_archive_file_name()}"
        )

    def log_metadata(self, experiment, filename):
        """
        {
         "experimentKey": "10bd1d749bfe48cd933c7e313e7376cd",
         "experimentName": "unusual_eagle_8578",
         "optimizationId": "e1679352eab540febb90f9155af5e907",
         "userName": "dsblank",
         "projectId": "8c42c401d9554dcdb5813e9df9c89b58",
         "projectName": "aitk-network",
         "workspaceName": "dsblank",
         "filePath": "Jupyter interactive",
         "fileName": "Jupyter interactive",
         "throttle": false, "throttleMessage": "",
         "throttlingReasons": [],
         "durationMillis": 35312,
         "startTimeMillis": 1618443472116,
         "endTimeMillis": 1618443507428,
         "running": false,
         "error": null,
         "hasCrashed": false,
         "archived": false,
         "tags": ["tag7", "tag8"],
         "cometDownloadVersion": "1.2.4"
         }
        """
        if self.debug:
            print("log_metadata...")
        if os.path.exists(filename):
            metadata = json.load(open(filename))
            experiment.add_tags(metadata["tags"])
            if metadata["fileName"] == "Jupyter interactive":
                experiment.set_filename(metadata["fileName"])
            elif metadata["fileName"] is not None:
                experiment.set_filename(os.path.join(metadata["fileName"]))

    def log_system_details(self, experiment, filename):
        """
        {
         "experimentKey": "10bd1d749bfe48cd933c7e313e7376cd",
         "user": "root",
         "pythonVersion": "3.7.10",
         "pythonVersionVerbose": "3.7.10 (default, Feb 20 2021, 21:17:23) \n[GCC 7.5.0]",
         "pid": 4923,
         "osType": "Linux",
         "os": "Linux-4.19.112+-x86_64-with-Ubuntu-18.04-bionic",
         "osRelease": "4.19.112+",
         "machine": "x86_64",
         "processor": "x86_64",
         "ip": "172.28.0.2",
         "hostname": "6bd59496ca63",
         "env": {"NO_GCE_CHECK": "True", ...}",
         "gpuStaticInfoList": [],
         "logAdditionalSystemInfoList": [],
         "systemMetricNames": ["sys.cpu.percent.02", "sys.cpu.percent.01", "sys.ram.total", "sys.cpu.percent.avg", "sys.ram.used"],
         "maxTotalMemory": null,
         "networkInterfaceIps": null,
         "command": ["/usr/local/lib/python3.7/dist-packages/ipykernel_launcher.py", "-f", "/root/.local/share/jupyter/runtime/kernel-d698a690-b9e0-4e47-ad8a-cfbc2de3c1f1.json"],
         "executable": "/usr/bin/python3",
         "totalRam": 13653573632.0
        }
        """
        if self.debug:
            print("log_system_details...")
        if os.path.exists(filename):
            system = json.load(open(filename))

            ## System info:
            message = SystemDetailsMessage.create(
                context=experiment.context,
                use_http_messages=experiment.streamer.use_http_messages,
                command=system["command"],
                env=system["env"],
                hostname=system["hostname"],
                ip=system["ip"],
                machine=system["machine"],
                os_release=system["osRelease"],
                os_type=system["osType"],
                os=system["os"],
                pid=system["pid"],
                processor=system["processor"],
                python_exe=system["executable"],
                python_version_verbose=system["pythonVersionVerbose"],
                python_version=system["pythonVersion"],
                user=system["user"],
            )
            experiment._enqueue_message(message)

    def log_graph(self, experiment, filename):
        if self.debug:
            print("log_graph...")
        if os.path.exists(filename):
            experiment.set_model_graph(open(filename).read())

    def log_assets(self, experiment, path, assets_metadata):
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
        if self.debug:
            print("log_assets...")
        for log_filename in assets_metadata:
            asset_type = assets_metadata[log_filename].get("type", None)
            asset_type = asset_type if asset_type else "asset"
            if asset_type in self.ignore:
                continue
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

    def log_code(self, experiment, filename):
        """ """
        if self.debug:
            print("log_code...")
        if os.path.exists(filename):
            if os.path.isfile(filename):
                experiment.log_code(str(filename))
            elif os.path.isdir(filename):
                experiment.log_code(folder=str(filename))

    def log_requirements(self, experiment, filename):
        """
        Requirements (pip packages)
        """
        if self.debug:
            print("log_requirements...")
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

    def log_metrics(self, experiment, filename):
        """ """
        if self.debug:
            print("log_metrics...")
        if os.path.exists(filename):
            for line in open(filename):
                dict_line = json.loads(line)
                name = dict_line["metricName"]
                if name.startswith("sys.") and "system-metrics" in self.ignore:
                    continue
                value = dict_line["metricValue"]
                step = dict_line["step"]
                epoch = dict_line["epoch"]
                context = dict_line["runContext"]
                timestamp = dict_line["timestamp"]
                # FIXME: does not log time, duration
                message = MetricMessage(
                    context=context,
                    timestamp=timestamp,
                )
                message.set_metric(name, value, step=step, epoch=epoch)
                experiment._enqueue_message(message)

    def log_parameters(self, experiment, filename):
        """ """
        if self.debug:
            print("log_parameters...")
        if os.path.exists(filename):
            parameters = json.load(open(filename))
            for parameter in parameters:
                name = parameter["name"]
                value = parameter["valueCurrent"]
                experiment.log_parameter(name, value)

    def log_others(self, experiment, filename):
        """ """
        if self.debug:
            print("log_others...")
        if os.path.exists(filename):
            for line in open(filename):
                dict_line = json.loads(line)
                name = dict_line["name"]
                value = dict_line["valueCurrent"]
                experiment.log_other(key=name, value=value)

    def log_output(self, experiment, output_file):
        """ """
        if self.debug:
            print("log_output...")
        if os.path.exists(output_file):
            for line in open(output_file):
                message = StandardOutputMessage.create(
                    context=experiment.context,
                    use_http_messages=experiment.streamer.use_http_messages,
                    output=line,
                    stderr=False,
                )
                experiment._enqueue_message(message)

    def log_html(self, experiment, filename):
        if self.debug:
            print("log_html...")
        if os.path.exists(filename):
            html = open(filename).read()
            message = HtmlMessage.create(
                context=experiment.context,
                use_http_messages=experiment.streamer.use_http_messages,
                html=html,
            )
            experiment._enqueue_message(message)

    def log_git_metadata(self, experiment, filename):
        if os.path.exists(filename):
            with open(filename) as fp:
                metadata = json.load(fp)

            git_metadata = {
                "parent": metadata["parent"],
                "repo_name": None,
                "status": None,
                "user": metadata["user"],
                "root": metadata["root"],
                "branch": metadata["branch"],
                "origin": metadata["origin"],
            }
            message = GitMetadataMessage.create(
                context=experiment.context,
                use_http_messages=experiment.streamer.use_http_messages,
                git_metadata=git_metadata,
            )
            experiment._enqueue_message(message)

    def log_git_patch(self, experiment, filename):
        if os.path.exists(filename):
            with open(filename) as fp:
                git_patch = fp.read()

            _, zip_path = compress_git_patch(git_patch)
            processor = GitPatchUploadProcessor(
                TemporaryFilePath(zip_path),
                experiment.asset_upload_limit,
                url_params=None,
                metadata=None,
                copy_to_tmp=False,
                error_message_identifier=None,
                tmp_dir=experiment.tmpdir,
                critical=False,
            )
            upload_message = processor.process()
            if upload_message:
                experiment._enqueue_message(upload_message)

    def log_all(self, experiment, experiment_folder):
        """ """
        # FIXME: missing notes (edited by human, not logged programmatically)
        if "metrics" not in self.ignore:
            self.log_metrics(
                experiment, os.path.join(experiment_folder, "metrics.jsonl")
            )

        if "metadata" not in self.ignore:
            self.log_metadata(
                experiment, os.path.join(experiment_folder, "metadata.json")
            )

        if "parameters" not in self.ignore:
            self.log_parameters(
                experiment, os.path.join(experiment_folder, "parameters.json")
            )

        if "others" not in self.ignore:
            self.log_others(experiment, os.path.join(experiment_folder, "others.jsonl"))

        if "assets" not in self.ignore:
            assets_metadata_filename = os.path.join(
                experiment_folder, "assets", "assets_metadata.jsonl"
            )
            assets_metadata = {}
            if os.path.exists(assets_metadata_filename):
                for line in open(assets_metadata_filename):
                    data = json.loads(line)
                    assets_metadata[data["fileName"]] = data

                self.log_assets(
                    experiment,
                    os.path.join(experiment_folder, "assets"),
                    assets_metadata,
                )

        if "output" not in self.ignore:
            self.log_output(
                experiment, os.path.join(experiment_folder, "run/output.txt")
            )

        if "requirements" not in self.ignore:
            self.log_requirements(
                experiment, os.path.join(experiment_folder, "run/requirements.txt")
            )

        if "model-graph" not in self.ignore:
            self.log_graph(
                experiment, os.path.join(experiment_folder, "run/graph_definition.txt")
            )

        if "html" not in self.ignore:
            self.log_html(
                experiment,
                os.path.join(experiment_folder, "experiment.html"),
            )

        if "system-details" not in self.ignore:
            self.log_system_details(
                experiment, os.path.join(experiment_folder, "system_details.json")
            )

        if "git" not in self.ignore:
            self.log_git_metadata(
                experiment, os.path.join(experiment_folder, "run", "git_metdata.json")
            )
            self.log_git_patch(
                experiment, os.path.join(experiment_folder, "run", "git_diff.patch")
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
