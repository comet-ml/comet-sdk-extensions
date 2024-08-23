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
* experiment
* image
* asset
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
from typing import List, Optional

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
        help=(
            "Items to include (optional, default is optimizer, mpm, metric, experiment, image, asset)"
        ),
        nargs="*",
        default=[],
    )
    parser.add_argument(
        "--exclude",
        help=("Items to exclude (optimizer, mpm, metric, experiment, image, asset)"),
        nargs="*",
        default=[],
    )
    parser.add_argument(
        "--debug",
        help=("Show debugging information"),
        default=False,
    )


def _create_image(
    text,
    height=50,
    margin=None,
    color=(255, 255, 255),
    background_color=(0, 0, 0),
    randomness=0,
):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise ImportError(
            "pillow not installed; run `pip install pillow` to install it"
        ) from None

    font = ImageFont.load_default(size=height)
    (0, 12, 112, 50)
    x, y, width, height = font.getbbox(text)
    margin = margin if margin is not None else int(height / 5)
    image = Image.new(
        "RGB", (width + margin * 2, height + margin * 2), background_color
    )
    draw = ImageDraw.Draw(image)
    fudge = int(height * (7 / 50))
    draw.text((margin, margin - fudge), text, color, font=font)
    for i in range(randomness):
        draw.point(
            (
                random.randint(0, width + margin * 2),
                random.randint(0, height + margin * 2),
            ),
            fill=color,
        )
    return image


def _log_mpm_events(MPM: any, nb_events: int, days: int) -> None:
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


def _log_mpm_training_distribution(MPM: any, nb_events: int) -> None:
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
                random.choices(["a", "b", "c"], [0.1, 0.2, 0.7])[0],
                random.choice([True, False]),
                random.uniform(0, 1),
                random.choice([True, False]),
            ]
            writer.writerow(row)

        fp.flush()

        # Log the training distribution to MPM
        MPM.upload_dataset_csv(
            file_path=fp.name,
            dataset_type="TRAINING_EVENTS",
            dataset_name="training_dataset-%s" % random.randint(100000, 999999),
        )


def test_mpm(workspace: str, model_name: str, nb_events: int, days: int):
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
        ) from None

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
    includes: List[str],
    workspace: str,
    project_name: str,
    name: str,
):
    """
    Args:
        workspace (str): workspace name
        project_name (str): project_name
    """
    print("    Attempting to create an experiment...")
    experiment = Experiment(workspace=workspace, project_name=project_name)
    key = experiment.get_key()
    experiment.set_name(name)

    if "dataset-info" in includes:
        # Dataset info:
        print("    Attempting to log a dataset...")
        experiment.log_dataset_info(
            name="mnist", version="1.6.8", path="/opt/share/datasets/mnist.db"
        )

    if "metric" in includes:
        print("    Attempting to log metrics...")
        for step in range(100):
            experiment.log_metric("accuracy", random.random() * step, step=step)
            experiment.log_metric("loss", 100 - (random.random() * step), step=step)

    if "image" in includes:
        print("    Attempting to log an image...")
        image = _create_image("smoke-test")
        experiment.log_image(image, "smoke-test-image.png", step=0)

    if "asset" in includes:
        print("    Attempting to log an asset...")
        data = {
            "key1": 1,
            "key2": {
                "key2-1": 1.1,
                "key2-2": 1.2,
            },
        }
        experiment.log_asset_data(data, "smoke-test.json")

    if "confusion-matrix" in includes:
        print("    Attempting to log a confusion matrix...")
        y_true = [(i % 10) for i in range(500)]
        y_predicted = [random.randint(0, 9) for i in range(500)]
        images = [_create_image(str(n), margin=30, randomness=30) for n in y_true]
        experiment.log_confusion_matrix(y_true, y_predicted, images=images, step=0)

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
        parsed_args.include
        if parsed_args.include
        else ["mpm", "optimizer", "experiment"]
    )
    for item in parsed_args.exclude:
        if item in includes:
            includes.remove(item)
    # Handle subitems:
    for item in ["image", "asset", "metric", "dataset-info", "confusion-matrix"]:
        if item not in parsed_args.exclude and "experiment" in includes:
            includes.append(item)

    workspace, project_name = parsed_args.COMET_PATH.split("/", 1)
    print("Running cometx smoke tests...")
    print("Using %s/%s on %s" % (workspace, project_name, comet_base_url))

    if "experiment" in includes:
        print("    Attempting to log experiment...")
        project_data = api.get_project(workspace, project_name) or {}
        # Test Experiment
        key = test_experiment(
            includes,
            workspace,
            project_name,
            "test-%s" % (project_data.get("numberOfExperiments", 0) + 1),
        )
        experiment = api.get_experiment_by_key(key)

        if "metric" in includes:
            metric = experiment.get_metrics("loss")
            while len(metric) == 0 or "metricName" not in metric[0]:
                print("Waiting on metrics to finish processing...")
                time.sleep(5)
                metric = experiment.get_metrics("loss")

            if "metricName" in metric[0] and metric[0]["metricValue"]:
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
        test_mpm(workspace, project_name, nb_events=10, days=7)

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
