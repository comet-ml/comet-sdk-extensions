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
#  Copyright (c) 2024 Cometx Development
#      Team. All rights reserved.
# ****************************************
"""
Example:

Perform a smoke test on a Comet installation

$ cometx smoke-test WORKSPACE/PROJECT
"""
import argparse
import os
import sys
from typing import Optional

from comet_ml import API, APIExperiment, Experiment, Optimizer

ADDITIONAL_ARGS = False


def get_parser_arguments(parser):
    parser.add_argument(
        "COMET_PATH",
        help=("The Comet workspace/project to log tests"),
        type=str,
    )
    parser.add_argument(
        "--exclude",
        help=("Items to exclude (optimizer)"),
        nargs="*",
        default=[],
    )
    parser.add_argument(
        "--image",
        help=("Path to image"),
        type=str,
    )
    parser.add_argument(
        "--asset",
        help=("Path to asset file"),
        type=str,
    )


def test_experiment(
    workspace: str,
    project_name: str,
    image_path: Optional[str] = None,
    file_path: Optional[str] = None,
):
    """
    Args:
        workspace (str): workspace name
        project_name (str): project_name
        image_path (str, optional): image_path
        file_path (str, optional): file_path
    """
    experiment = Experiment(workspace=workspace, project_name=project_name)
    key = experiment.get_key()
    experiment.set_name("header test")
    # Types:
    # Dataset info:
    experiment.log_dataset_info(
        name="test dataset", version="test1", path="/test/file/path"
    )
    # Metrics:
    experiment.log_metric("int_metric", 42.5, step=0)
    experiment.log_metrics(
        {
            "dict_metric_str": "foo",
            "dict_metric_int": 33,
            "dict_metric_bool": True,
        },
        step=0,
    )
    # Image:
    if image_path:
        experiment.log_image(image_path)
    # Assets:
    if file_path:
        experiment.log_asset(file_path)
    experiment.end()
    return key


def test_optimizer(workspace: str, project_name: str):
    """
    Args:
        workspace (str): workspace
        project_name (str): project_name
    """
    optimizer_config = {
        "algorithm": "bayes",
        "name": "Optimizer Test",
        "spec": {
            "maxCombo": 10,
            "objective": "minimize",
            "metric": "loss",
        },
        "parameters": {
            "x": {"type": "float", "min": -6, "max": 5},
        },
    }

    def objective_function(x: float) -> float:  # pylint: disable=invalid-name
        """Objective function to minimize."""
        return x * x

    opt = Optimizer(optimizer_config)
    count = 0
    for experiment in opt.get_experiments(
        workspace=workspace, project_name=project_name
    ):
        print("Trying:", experiment.params)
        loss = objective_function(experiment.params["x"])
        experiment.log_metric("loss", loss, step=0)
        count += 1
        experiment.end()
        print("Optimizer job done! Completed %d experiments." % count)
    count = 0


def smoke_test(parsed_args, remaning=None) -> None:
    """
    Runs the smoke tests.
    """
    # Use API to get API Key and URL (includes smart key usage)
    api = API()

    comet_base_url = api.config["comet.url_override"]
    if comet_base_url.endswith("/"):
        comet_base_url = comet_base_url[:-1]
    if comet_base_url.endswith("/clientlib"):
        comet_base_url = comet_base_url[:10]

    os.environ["COMET_OPTIMIZER_URL"] = comet_base_url + "/optimizer/"

    workspace, project_name = parsed_args.COMET_PATH.split("/", 1)

    # Test Experiment
    key = test_experiment(
        workspace,
        project_name,
        parsed_args.image,
        parsed_args.asset,
    )
    experiment = APIExperiment(
        previous_experiment=key,
    )
    metric = experiment.get_metrics("int_metric")
    if "metricName" in metric[0] and metric[0]["metricValue"] == "42.5":
        print("\nSuccessfully validated metric presence\n")
    else:
        print("\nSomething is wrong\n")

    # Optimizer
    if "optimizer" not in parsed_args.exclude:
        test_optimizer(
            workspace=workspace,
            project_name=project_name,
        )


def main(args):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    get_parser_arguments(parser)
    parsed_args = parser.parse_args(args)

    smoke_test(parsed_args)


if __name__ == "__main__":
    # Called via `python -m cometx.cli.smoke_test ...`
    main(sys.argv[1:])
