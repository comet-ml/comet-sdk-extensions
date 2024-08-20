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

$ cometx smoke-test WORKSPACE/PROJECT --test all
"""
import argparse
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
from comet_ml import API, APIExperiment, Experiment, Optimizer

ADDITIONAL_ARGS = False


def get_parser_arguments(parser):
    parser.add_argument(
        "COMET_PATH",
        help=("The Comet workspace/project to log tests"),
        type=str,
    )
    parser.add_argument(
        "--test",
        help=("Specify which tests to run"),
        choices=["all", "experiment", "optimizer", "mpm"],
        default="all",
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

def _log_mpm_events(MPM: any, nb_events: int = 1000):
    # Create test data
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)
    timestamps = [start_date + timedelta(seconds=random.randint(0, 7*24*60*60)) for _ in range(1000)]
    timestamps.sort()  # Sort timestamps in ascending order

    test_data = [
        {
            "prediction_id": str(uuid.uuid4()),
            "timestamp": int(ts.timestamp()),
            "input_features": {
                "numerical_feature": random.uniform(0, 100),
                "categorical_feature": random.choice(["a", "b", "c"])
            },
            "output_features": {
                "value": random.choice([True, False]),
                "probability": random.uniform(0, 1)
            },
            "labels": {
                "label": random.choice([True, False])
            }
        }
        for ts in timestamps
    ]

    # Log the test data to MPM
    for data_point in test_data:
        MPM.log_event(**data_point)
    
    return test_data

def _log_mpm_training_distribution(MPM: any, nb_events: int = 10000):
    # Create training distribution
    df = pd.DataFrame({
        'feature_numerical_feature': np.random.uniform(0, 100, nb_events),
        'feature_categorical_feature': np.random.choice(['a', 'b', 'c'], nb_events, p=[0.1, 0.2, 0.7]),
        'prediction_value': np.random.choice([True, False], nb_events),
        'prediction_probability': np.random.uniform(0, 1, nb_events),
        'label_value_label': np.random.choice([True, False], nb_events)
    })

    # Write the training distribution DataFrame to a CSV file
    temp_csv_path = 'temp_training_distribution.csv'
    df.to_csv(temp_csv_path, index=False)

    # Log the training distribution to MPM
    MPM.upload_dataset_csv(
        file_path=temp_csv_path,
        dataset_type="TRAINING_EVENTS",
        dataset_name="training_dataset"
    )

    # Remove the temporary CSV file
    os.remove(temp_csv_path)

    return df



def test_mpm(workspace: str, model_name: str, nb_events: int = 1000):
    """
    Args:
        workspace (str): workspace
        model_name (str): model_name
    """

    try:
        import comet_mpm
    except ImportError:
        raise ImportError(
            "comet_mpm not installed, run `pip install comet-mpm` to install it"
        )

    MPM = comet_mpm.CometMPM(
        workspace_name=workspace,
        model_name=model_name,
        model_version="1.0.0",
        max_batch_time=1
    )

    # Log MPM events
    _log_mpm_events(MPM, nb_events)

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


def _get_comet_base_url():
    # Use API to get API Key and URL (includes smart key usage)
    api = API()

    comet_base_url = api.config["comet.url_override"]

    if comet_base_url.endswith("/"):
        comet_base_url = comet_base_url[:-1]
    if comet_base_url.endswith("/clientlib"):
        comet_base_url = comet_base_url[:-10]

    return comet_base_url

def smoke_test(parsed_args, remaning=None) -> None:
    """
    Runs the smoke tests.
    """
    workspace, project_name = parsed_args.COMET_PATH.split("/", 1)

    comet_base_url = _get_comet_base_url()

    if parsed_args.test in ["all", "experiment"]:
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
    
    if parsed_args.test in ["all", "optimizer"]:
        os.environ["COMET_OPTIMIZER_URL"] = comet_base_url + "/optimizer/"

        # Optimizer
        test_optimizer(
            workspace=workspace,
            project_name=project_name,
        )
        print("\nCompleted Optimizer test, you will need to check the Comet UI to ensure all the data has been correctly logged.\n")

    if parsed_args.test in ["all", "mpm"]:
        test_mpm(workspace, project_name)
        comet_mpm_ui_url = comet_base_url + f"/{workspace}#model-production-monitoring"
        print(f"\nCompleted MPM test, you will need to check the MPM UI ({comet_mpm_ui_url}) to validate the data has been logged, this can take up to 5 minutes.\n")

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
