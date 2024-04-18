# -*- coding: utf-8 -*-
# ****************************************
#                               __
#    _________  ____ ___  ___  / /__  __
#   / ___/ __ \/ __ `__ \/ _ \/ __/ |/ /
#  / /__/ /_/ / / / / / /  __/ /_ >   <
#  \___/\____/_/ /_/ /_/\___/\__//_/|_/
#
#     Copyright (c) 2023-2024 Cometx
#  Development Team. All rights reserved.
# ****************************************

import json
import math
import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote

import wandb
from comet_ml.cli_args_parse import _parse_cmd_args, _parse_cmd_args_naive
from comet_ml.utils import makedirs

from ..utils import download_url, remove_extra_slashes

MAX_METRIC_SAMPLES = 15_000


class DownloadManager:
    def __init__(
        self,
        include=None,
        ignore=None,
        output=None,
        list_items=False,
        flat=False,
        force=False,
        filename=None,
        asset_type=None,
        overwrite=False,
        skip=False,
        debug=False,
        query=None,
        max_workers=1,
    ):
        self.api = wandb.Api(timeout=60)

        self.root = output if output is not None else os.getcwd()
        self.debug = debug
        self.flat = flat
        self.skip = skip
        self.force = force
        self.filename = filename
        self.asset_type = asset_type
        self.overwrite = overwrite
        if max_workers > 1:
            self.queue = ThreadPoolExecutor(max_workers=max_workers)
        else:
            self.queue = None
        self.ignore = ignore if ignore else []
        self.include_experiments = None

    def download_file_task(self, path, file):
        def task():
            with tempfile.TemporaryDirectory() as tmpdir:
                file.download(root=tmpdir)
                shutil.copy(os.path.join(tmpdir, file.name), path)

        if self.queue is None:
            # Do it now:
            task()
        else:
            # add to queue
            self.queue.submit(task)

    def end(self):
        if self.queue is not None:
            self.queue.shutdown(wait=True)

    def reset_run(self):
        self.asset_metadata = []
        self.parameters = []

    def download(self, PATH):
        path = remove_extra_slashes(PATH)
        path_parts = path.split("/")
        if len(path_parts) == 2:
            workspace, project = path_parts
            self.include_experiments = None
        elif len(path_parts) == 3:
            workspace, project, experiment = path_parts
            self.include_experiments = [experiment]
        elif len(path_parts) == 4 and path_parts[2] == "runs":
            workspace, project, _, experiment = path_parts
            self.include_experiments = [experiment]
        else:
            raise Exception("invalid PATH: %r" % PATH)

        projects = [project]

        # Download items:
        for project in projects:
            # FIXME: PDF only show first exposed charts; ignore for now
            # if "reports" not in self.ignore:
            #    self.download_reports(workspace, project)
            self.download_runs(workspace, project)

    def get_path(self, run, *subdirs, filename=None):
        if self.flat:
            path = self.root
        else:
            workspace, project, experiment = run.path
            path = os.path.join(self.root, workspace, project, experiment, *subdirs)
        makedirs(path, exist_ok=True)
        if filename:
            path = os.path.join(path, filename)
            # Add to asset metadata:
            if (
                len(subdirs) > 1
                and subdirs[0] == "assets"
                and subdirs[1] != "assets_metadata.jsonl"
            ):
                self.asset_metadata.append(
                    {
                        "fileName": filename,
                        "type": subdirs[1],
                    }
                )
        return path

    def get_file_path(self, wandb_file):
        return "/".join(wandb_file.name.split("/")[:-1])

    def get_file_name(self, wandb_file):
        return wandb_file.name.split("/")[-1]

    def download_cmd_parameters(self, run, args):
        print("    downloading parameters...")
        try:
            args = _parse_cmd_args(args)
        except ValueError:
            args = _parse_cmd_args_naive(args)

        if args:
            self.parameters = []
            for key, value in args.items():
                self.parameters.append(
                    {
                        "name": key,
                        "valueMax": value,
                        "valueMin": value,
                        "valueCurrent": value,
                        "editable": False,
                    }
                )

    def download_file(self, path, file):
        with tempfile.TemporaryDirectory() as tmpdir:
            file.download(root=tmpdir)
            shutil.copy(os.path.join(tmpdir, file.name), path)

    def download_data(self, path, data):
        with open(path, "w") as fp:
            fp.write(data + "\n")

    def download_model_graph(self, run, file):
        print("    downloading model graph...")
        path = self.get_path(run, "run", filename="graph_definition.txt")
        self.download_file_task(path, file)

    def download_model(self, run, file):
        print("    downloading model...")
        filename = self.get_file_name(file)
        path = self.get_path(run, "assets", "model-element", filename=filename)
        self.download_file_task(path, file)

    def download_image(self, run, file):
        print("    downloading image...")
        filename = self.get_file_name(file)
        path = self.get_path(run, "assets", "image", filename=filename)
        self.download_file_task(path, file)

    def download_asset(self, run, file):
        print("    downloading asset...")
        filename = self.get_file_name(file)
        path = self.get_path(run, "assets", "asset", filename=filename)
        self.download_file_task(path, file)

    def download_asset_data(self, run, data, filename):
        path = self.get_path(run, "assets", "asset", filename=filename)
        self.download_data(path, data)

    def download_code(self, run, file):
        print("    downloading code...")
        path = self.get_path(run, "run", filename="script.py")
        self.download_file_task(path, file)

    def download_output(self, run, file):
        print("    downloading output...")
        path = self.get_path(run, "run", filename="output.txt")
        self.download_file_task(path, file)

    def download_dependencies(self, run, file):
        print("    downloading dependencies...")
        path = self.get_path(run, "run", filename="requirements.txt")
        self.download_file_task(path, file)

    def download_asset_metadata(self, run):
        path = self.get_path(run, "assets", filename="assets_metadata.jsonl")
        with open(path, "w") as fp:
            for metadata in self.asset_metadata:
                fp.write(json.dumps(metadata) + "\n")

    def download_others(self, run, data):
        print("    downloading others...")
        filename = self.get_path(run, filename="others.jsonl")
        with open(filename, "w") as fp:
            for key, value in data.items():
                data_json = {
                    "name": key,
                    "valueMax": str(value),
                    "valueMin": str(value),
                    "valueCurrent": str(value),
                    "editable": False,
                }
                fp.write(json.dumps(data_json) + "\n")

    def download_runs(self, workspace, project):
        runs = self.api.runs(f"{workspace}/{project}")
        for run in reversed(runs):
            # Handle all of the basic run items here:
            _, _, experiment = run.path
            # Skip if experiment is not one to download:
            if not (
                self.include_experiments is None
                or experiment in self.include_experiments
            ):
                continue

            # Skip if already downloaded, and not force:
            if (
                os.path.exists(os.path.join(workspace, project, experiment))
                and not self.force
            ):
                print(f"skipping {workspace}/{project}/{experiment}...")
                continue

            print(
                f"downloading run {run.name} to {workspace}/{project}/{experiment}..."
            )
            self.reset_run()
            others = {
                "Name": run.name,
                "origin": run.url,
            }
            if "-run-" in run.name:
                group, count = run.name.rsplit("-run-", 1)
                others["Group"] = group
                others["Run"] = "run-" + count
            else:
                others["Group"] = run.name
                others["Run"] = run.name
            # Handle all of the specific run items below:
            if "metrics" not in self.ignore:
                self.download_metrics(run)

            # Handle assets (things that have a filename) here:
            for file in list(run.files()):
                path = self.get_file_path(file)
                name = file.name
                if name.startswith("artifact/"):
                    self.download_artifact(run, file)

                elif path == "media/graph" and "graph" not in self.ignore:
                    self.download_model_graph(run, file)
                elif path == "code" and "code" not in self.ignore:
                    self.download_code(run, file)
                elif name == "output.log" and "output" not in self.ignore:
                    self.download_output(run, file)
                elif name == "requirements.txt":
                    self.download_dependencies(run, file)
                elif name == "wandb-summary.json":
                    with tempfile.TemporaryDirectory() as tmpdirname:
                        summary = json.load(file.download(root=tmpdirname))
                        # list of all of the metrics, etc
                        self.download_asset_data(
                            run, json.dumps(summary), "wandb_summary.json"
                        )
                elif name == "wandb-metadata.json":
                    ## System info etc
                    self.download_system_details(run, file)
                elif name == "diff.patch":
                    self.download_git_patch(run, file)
                elif "media/images" in path:
                    self.download_image(run, file)
                elif any(
                    extension in name
                    for extension in [
                        ".pb",
                        ".onnx",
                        ".pkl",
                        ".mlmodel",
                        ".pmml",
                        ".pt",
                        ".h5",
                    ]
                ):
                    self.download_model(run, file)
                else:
                    self.download_asset(run, file)

            # After all of the file downloads, log others:
            self.download_others(run, others)
            self.download_asset_metadata(run)
            self.download_hyper_parameters(run.config)
            self.write_parameters(run)

    def download_git_patch(self, run, file):
        path = self.get_path(run, "run", filename="git_diff.patch")
        self.download_file_task(path, file)

    def download_hyper_parameters(self, config):
        # FIXME: may need to unpack these
        for key, value in config.items():
            self.parameters.append(
                {
                    "name": key,
                    "valueMax": value,
                    "valueMin": value,
                    "valueCurrent": value,
                    "editable": False,
                }
            )

    def write_parameters(self, run):
        path = self.get_path(run, filename="parameters.json")
        with open(path, "w") as fp:
            fp.write(json.dumps(self.parameters) + "\n")

    def download_system_details(self, run, file):
        with tempfile.TemporaryDirectory() as tmpdirname:
            system_and_os_info = json.load(file.download(root=tmpdirname))
        args = system_and_os_info["args"]
        system_details = {
            "command": (
                [system_and_os_info["program"]] + args
                if args
                else [system_and_os_info["program"]]
            ),
            "env": None,
            "hostname": system_and_os_info["host"],
            "ip": "",
            "machine": "",
            "osRelease": system_and_os_info["os"],
            "osType": system_and_os_info["os"],
            "os": system_and_os_info["os"],
            "pid": 0,
            "processor": "",
            "executable": system_and_os_info["executable"],
            "pythonVersionVerbose": system_and_os_info["python"],
            "pythonVersion": system_and_os_info["python"],
            "user": system_and_os_info["username"],
        }
        path = self.get_path(run, filename="system_details.json")
        with open(path, "w") as fp:
            fp.write(json.dumps(system_details) + "\n")
        # ---
        self.download_cmd_parameters(run, args)
        # ---
        if "git" in system_and_os_info:
            commit = system_and_os_info["git"]["commit"]
            origin = system_and_os_info["git"]["remote"]
            git_metadata = {
                "parent": commit,
                "user": None,
                "root": None,
                "branch": None,
                "origin": origin,
            }
            path = self.get_path(run, "run", filename="git_metadata.json")
            with open(path, "w") as fp:
                fp.write(json.dumps(git_metadata) + "\n")
        """
        # FIXME:
        # Set the filename separately
        ## self.experiment.set_filename(system_and_os_info['program'])
        """
        # Log the entire file as well:
        path = self.get_path(run, "assets", filename="wandb-metadata.json")
        with open(path, "w") as fp:
            fp.write(json.dumps(system_and_os_info) + "\n")

    def download_artifact(self, run, file):
        _, artifact_id, artifact_name = file.name.split("/", 2)
        path = self.get_path(run, "artifacts", artifact_id, filename=artifact_name)
        self.download_file_task(path, file)

    def download_artifact_by_name(
        self,
        workspace,
        project,
        artifact_name,
        alias,
    ):
        # Utility, not used here
        """
        Example:

        ```python
        download_table(
            "stacey",
            "mnist-viz",
            "baseline",
            "v4",
        )
        ```
        """
        if self.flat:
            path = self.root
        else:
            path = os.path.join(self.root, workspace, project, "artifacts")

        makedirs(path, exist_ok=True)
        artifact = self.api.artifact(f"{workspace}/{project}/{artifact_name}:{alias}")
        artifact.download(path)

    def ignore_metric_name(self, metric):
        """
        Example:

        cometx download --from wandb ... --ignore "metrics:.*/avg"
        """
        if metric.startswith("_"):
            return True
        # Ignore any matches:
        for ignore in self.ignore:
            if ignore.startswith("metrics:"):
                _, regex = ignore.split(":", 1)
                if re.match(regex, metric):
                    return True
        return False

    def download_metric_task(self, metric, run, count):
        def task():
            print("        downloading metric %r..." % metric)
            metric_data = run.history(
                keys=[metric, "_timestamp"],
                pandas=False,
                samples=MAX_METRIC_SAMPLES,
            )
            filename = self.get_path(
                run, "metrics", filename="metric_%05d.jsonl" % count
            )
            with open(filename, "w") as fp:
                for row in metric_data:
                    step = row.get("_step", None)
                    timestamp = row.get("_timestamp", None)
                    value = row.get(metric, None)
                    if isinstance(value, dict):
                        # ignore here; artifacts or summary metrics?
                        pass
                    else:
                        if (
                            metric is not None
                            and value is not None
                            and not math.isnan(value)
                        ):
                            ts = (
                                int(timestamp * 1000) if timestamp is not None else None
                            )
                            data = {
                                "metricName": metric,
                                "metricValue": value,
                                "timestamp": ts,
                                "step": step,
                                "epoch": None,
                                "runContext": None,
                            }
                            fp.write(json.dumps(data) + "\n")

        if self.queue is None:
            # Do it now:
            task()
        else:
            # add to queue
            self.queue.submit(task)

    def download_metrics(self, run):
        print("    downloading metrics...")
        metrics = list(run.history(pandas=False, samples=1)[0].keys())
        metrics_summary_path = self.get_path(run, filename="metrics_summary.jsonl")
        with open(metrics_summary_path, "w") as fp:
            for count, metric in enumerate(metrics):
                if self.ignore_metric_name(metric):
                    continue
                fp.write(json.dumps({"metric": metric, "count": count}) + "\n")
                self.download_metric_task(metric, run, count)

    def download_reports(self, workspace, project):
        if self.flat:
            path = self.root
        else:
            path = os.path.join(self.root, workspace, project, "reports")

        makedirs(path, exist_ok=True)
        wandb_path = workspace + "/" + project
        reports = self.api.reports(path=wandb_path)
        for report in reports:
            url = report.url
            report_name = unquote(url.split("/")[-1] + ".pdf")
            filepath = os.path.join(path, report_name)
            download_url(url, output_filename=filepath)
            report_data = {
                "workspace": workspace,
                "project": project,
                "url": url,
            }
            with open(os.path.join(path, "reports_metadata.jsonl"), "a+") as fp:
                fp.write(json.dumps(report_data))
                fp.write("\n")
