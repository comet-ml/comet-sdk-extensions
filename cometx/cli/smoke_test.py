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

Run all tests:
$ cometx smoke-test WORKSPACE/PROJECT

Run everything except mpm tests:
$ cometx smoke-test WORKSPACE/PROJECT --exclude mpm

Run just optimizer tests:
$ cometx smoke-test WORKSPACE/PROJECT optimizer

Run just metric tests:
$ cometx smoke-test WORKSPACE/PROJECT metric

Items:
* metric
* optimizer
* mpm
"""
import argparse
import csv
import datetime
import os
import random
import sys
import tempfile
import time
import uuid
from typing import Optional

from comet_ml import API, Experiment, Optimizer

ADDITIONAL_ARGS = False


def get_parser_arguments(parser):
    parser.add_argument(
        "COMET_PATH",
        help=("The Comet workspace/project to log tests"),
        type=str,
    )
    parser.add_argument(
        "include",
        help=("Items to include (optional, default is optimizer, mpm, metric)"),
        nargs="?",
        default=[],
    )
    parser.add_argument(
        "--exclude",
        help=("Items to exclude (optimizer, mpm, metric)"),
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


def _log_mpm_events(MPM: any, nb_events: int = 1000, days: int = 7) -> None:
    # Create test data
    end_date = datetime.datetime.now(datetime.timezone.utc)
    start_date = end_date - datetime.timedelta(days=days)
    timestamps = sorted(
        [
            start_date
            + datetime.timedelta(seconds=random.randint(0, days * 24 * 60 * 60))
            for _ in range(nb_events)
        ]
    )

    for ts in timestamps:
        data_point = {
            "prediction_id": str(uuid.uuid4()),
            "timestamp": int(ts.timestamp()),
            "input_features": {
                "numerical_feature": random.uniform(0, 100),
                "categorical_feature": random.choice(["a", "b", "c"]),
            },
            "output_features": {
                "value": random.choice([True, False]),
                "probability": random.uniform(0, 1),
            },
            "labels": {"label": random.choice([True, False])},
        }
        # Log the test data to MPM
        MPM.log_event(**data_point)


def _log_mpm_training_distribution(MPM: any, nb_events: int = 10000) -> None:
    # Create training distribution
    header = [
        "feature_numerical_feature",
        "feature_categorical_feature",
        "prediction_value",
        "prediction_probability",
        "label_value_label",
    ]

    with tempfile.NamedTemporaryFile("w", suffix=".csv", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(header)
        for _ in range(nb_events):
            row = [
                random.uniform(0, 100),
                random.choices(["a", "b", "c"], [0.1, 0.2, 0.7]),
                random.choice([True, False]),
                random.uniform(0, 1),
                random.choice([True, False]),
            ]
            writer.writerow(row)

        # Log the training distribution to MPM
        MPM.upload_dataset_csv(
            file_path=fp.name,
            dataset_type="TRAINING_EVENTS",
            dataset_name="training_dataset",
        )


def test_mpm(workspace: str, model_name: str, nb_events: int = 1000, days: int = 7):
    """
    Args:
        workspace (str): workspace
        model_name (str): model_name
    """
    try:
        import comet_mpm
    except ImportError:
        raise ImportError(
            "comet_mpm not installed; run `pip install comet-mpm` to install it"
        )

    MPM = comet_mpm.CometMPM(
        workspace_name=workspace,
        model_name=model_name,
        model_version="1.0.0",
        max_batch_time=1,
    )

    # Log MPM events
    _log_mpm_events(MPM, nb_events, days)

    # Log MPM training distribution
    _log_mpm_training_distribution(MPM, nb_events)

    # Call .end() method to make sure all data is logged to the platform
    MPM.end()


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
    print("    Attempting to create an experiment...")
    experiment = Experiment(workspace=workspace, project_name=project_name)
    key = experiment.get_key()
    experiment.set_name("header test")
    # Types:
    # Dataset info:
    print("    Attempting to log a dataset...")
    experiment.log_dataset_info(
        name="test dataset", version="test1", path="/test/file/path"
    )
    # Metrics:
    print("    Attempting to log metrics...")
    experiment.log_metric("int_metric", 42.5, step=0)
    experiment.log_metrics(
        {
            "dict_metric_str": "foo",
            "dict_metric_int": 33,
        },
        step=0,
    )
    # Image:
    if image_path:
        print("    Attempting to log an image...")
        experiment.log_image(image_path)
    # Assets:
    if file_path:
        print("    Attempting to log an asset...")
        experiment.log_asset(file_path)
    print("    Attempting to upload experiment...")
    experiment.end()
    print("Done!")
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
    api = API(cache=False)

    comet_base_url = api.config["comet.url_override"]
    if comet_base_url.endswith("/"):
        comet_base_url = comet_base_url[:-1]
    if comet_base_url.endswith("/clientlib"):
        comet_base_url = comet_base_url[:-10]

    includes = (
        parsed_args.include if parsed_args.include else ["mpm", "optimizer", "metric"]
    )
    for item in parsed_args.exclude:
        if item in includes:
            includes.remove(item)

    workspace, project_name = parsed_args.COMET_PATH.split("/", 1)
    print("Running cometx smoke tests...")
    print("Using %s/%s on %s" % (workspace, project_name, comet_base_url))

    # Test Experiment
    key = test_experiment(
        workspace,
        project_name,
        parsed_args.image,
        parsed_args.asset,
    )
    experiment = api.get_experiment_by_key(key)

    if "metric" in includes:
        metric = experiment.get_metrics("int_metric")
        while len(metric) == 0 or "metricName" not in metric[0]:
            print("Waiting on metrics to finish processing...")
            time.sleep(5)
            metric = experiment.get_metrics("int_metric")

        if "metricName" in metric[0] and metric[0]["metricValue"] == "42.5":
            print("\nSuccessfully validated metric presence\n")
        else:
            print("\nSomething is wrong\n")

    if "optimizer" in includes:
        print("    Attempting to run optimizer...")
        os.environ["COMET_OPTIMIZER_URL"] = comet_base_url + "/optimizer/"
        test_optimizer(
            workspace=workspace,
            project_name=project_name,
        )
        print(
            "\nCompleted Optimizer test, you will need to check the Comet UI to ensure all the data has been correctly logged.\n"
        )

    if "mpm" in includes:
        print("    Attempting to run mpm tests...")
        test_mpm(workspace, project_name)

        comet_mpm_ui_url = comet_base_url + f"/{workspace}#model-production-monitoring"
        print(
            f"\nCompleted MPM test, you will need to check the MPM UI ({comet_mpm_ui_url}) to validate the data has been logged, this can take up to 5 minutes.\n"
        )

    print("All tests have completed")


def main(args):
    formatter_class = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=formatter_class
    )
    get_parser_arguments(parser)
    parsed_args = parser.parse_args(args)

    smoke_test(parsed_args)


if __name__ == "__main__":
    # Called via `python -m cometx.cli.smoke_test ...`
    main(sys.argv[1:])
