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
Perform a smoke test on a Comet installation. Logs
results to WORKSPACE/smoke-tests or WORKSPACE/PROJECT.

Examples:

Run all tests:
$ cometx smoke-test WORKSPACE    # project defaults to smoke-tests
$ cometx smoke-test WORKSPACE/PROJECT

Run everything except mpm tests:
$ cometx smoke-test WORKSPACE/PROJECT --exclude mpm

Run just optimizer tests:
$ cometx smoke-test WORKSPACE/PROJECT optimizer

Run just metric tests:
$ cometx smoke-test WORKSPACE/PROJECT metric

Items to include or exclude:

* optimizer
* mpm
* panel
* experiment
  * metric
  * image
  * asset
  * dataset-info
  * confusion-matrix
  * embedding
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
from typing import List

from comet_ml import Experiment, Optimizer

from cometx.api import API

ADDITIONAL_ARGS = False
RESOURCES = {
    "experiment": [
        "image",
        "asset",
        "metric",
        "dataset-info",
        "confusion-matrix",
        "embedding",
    ],
    "optimizer": [],
    "mpm": [],
    "panel": [],
}
RESOURCES_ALL = sorted(
    list(RESOURCES.keys()) + [value for v in RESOURCES.values() for value in v]
)
RESOURCES_ALL_STR = ", ".join(RESOURCES_ALL)

BLUE = "\033[0;94m"
RED = "\033[0;91m"
GREEN = "\033[0;32m"
RESET = "\033[0m"


def get_parser_arguments(parser):
    parser.add_argument(
        "COMET_PATH",
        help=("The Comet workspace/project to log tests"),
        type=str,
    )
    parser.add_argument(
        "include",
        help=(f"Items to include; leave out for all, or any of: {RESOURCES_ALL_STR}"),
        nargs="*",
        default=[],
    )
    parser.add_argument(
        "--exclude",
        help=(f"Items to exclude; any of: {RESOURCES_ALL_STR}"),
        nargs="*",
        default=[],
    )
    parser.add_argument(
        "--debug",
        help=("Show debugging information"),
        default=False,
    )


def pprint(text: str, level: str = "info") -> None:
    """
    Print, with formatting
    """
    print(pformat(text, level))


def pformat(text: str, level: str = "info") -> str:
    """
    Format the text with colors.

    Args:
        text: the text to format
        info: the mode ("input" or "error")

    Returns a formatted string
    """
    if level == "info":
        return "%s%s%s" % (BLUE, text, RESET)
    elif level == "error":
        return "%s%s%s" % (RED, text, RESET)
    elif level == "good":
        return "%s%s%s" % (GREEN, text, RESET)
    else:
        return "%s%s%s" % (BLUE, text, RESET)


def _hex_to_rgb(hex_color):
    """
    Converts a hex color string to an RGB tuple.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


def _get_vector_from_image(image):
    """
    Get a vector from an image
    """
    vector = [
        image.getpixel((x, y))[0]
        for x in range(image.width)
        for y in range(image.height)
    ]
    return vector


def _create_image(
    text,
    height=50,
    margin=None,
    color=(255, 255, 255),
    background_color=(0, 0, 0),
    randomness=0,
    width=None,
):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise ImportError(
            "pillow not installed; run `pip install pillow` to install it"
        ) from None

    font = ImageFont.load_default(size=height)
    if width is None:
        x, y, font_width, font_height = font.getbbox(text)
        width = font_width
    margin = margin if margin is not None else int(height / 5)
    image = Image.new(
        "RGBA", (width + margin * 2, height + margin * 2), background_color
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


def test_mpm(api, workspace: str, model_name: str, nb_events: int, days: int):
    """
    Args:
        workspace (str): workspace
        model_name (str): model_name
    """
    try:
        import comet_mpm
    except ImportError:
        pprint(
            "comet_mpm not installed; run `pip install comet-mpm` to install it",
            "error",
        )
        pprint("Skipping mpm tests", "error")
        return

    MPM = comet_mpm.CometMPM(
        workspace_name=workspace,
        model_name=model_name,
        model_version="1.0.0",
        max_batch_time=1,
        api_key=api.config["comet.api_key"],
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
    pprint("    Attempting to create an experiment...", "info")
    experiment = Experiment(workspace=workspace, project_name=project_name)
    key = experiment.get_key()
    experiment.set_name(name)

    if "dataset-info" in includes:
        # Dataset info:
        pprint("    Attempting to log a dataset...", "info")
        experiment.log_dataset_info(
            name="mnist", version="1.6.8", path="/opt/share/datasets/mnist.db"
        )

    if "metric" in includes:
        pprint("    Attempting to log metrics...", "info")
        for step in range(100):
            experiment.log_metric("accuracy", random.random() * step, step=step)
            experiment.log_metric("loss", 100 - (random.random() * step), step=step)

    if "image" in includes:
        pprint("    Attempting to log an image...", "info")
        image = _create_image("smoke-test", background_color="red")
        experiment.log_image(image, "smoke-test-image.png", step=0)

    if "asset" in includes:
        pprint("    Attempting to log an asset...", "info")
        data = {
            "key1": 1,
            "key2": {
                "key2-1": 1.1,
                "key2-2": 1.2,
            },
        }
        experiment.log_asset_data(data, "smoke-test.json")

    if "confusion-matrix" in includes:
        pprint("    Attempting to log a confusion matrix...", "info")
        y_true = [(i % 10) for i in range(500)]
        y_predicted = [random.randint(0, 9) for i in range(500)]
        images = [_create_image(str(n), margin=30, randomness=30) for n in y_true]
        experiment.log_confusion_matrix(y_true, y_predicted, images=images, step=0)

    if "embedding" in includes:
        pprint("    Attempting to log embedding...", "info")
        labels = [str(i % 10) for i in range(100)]
        images = [
            _create_image(label, margin=0, randomness=30, width=30) for label in labels
        ]
        vectors = [_get_vector_from_image(image) for image in images]
        tables = [["label", "index", "score"]] + [
            [label, index, random.random()] for index, label in enumerate(labels)
        ]

        def get_color(index):
            label = str(index % 10)
            if label == "0":
                return _hex_to_rgb("#8b0000")  # darkred
            elif label == "1":
                return _hex_to_rgb("#0000ff")  # blue
            elif label == "2":
                return _hex_to_rgb("#008000")  # green
            elif label == "3":
                return _hex_to_rgb("#483d8b")  # darkslateblue
            elif label == "4":
                return _hex_to_rgb("#b8860b")  # darkgoldenrod
            elif label == "5":
                return _hex_to_rgb("#ff1493")  # deeppink
            elif label == "6":
                return _hex_to_rgb("#b22222")  # firebrick
            elif label == "7":
                return _hex_to_rgb("#228b22")  # forestgreen
            elif label == "8":
                return _hex_to_rgb("#8fbc8f")  # darkseagreen
            elif label == "9":
                return _hex_to_rgb("#9400d3")  # darkviolet

        experiment.log_embedding(
            vectors,
            tables,
            image_data=images,
            image_size=(30, 50),
            image_transparent_color=(0, 0, 0),
            image_background_color_function=get_color,
            title="Comet Embedding",
        )

    pprint("    Attempting to upload experiment...", "info")
    experiment.end()
    pprint("Done!", "good")
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
        workspace=workspace,
        project_name=project_name,
        log_env_details=False,
        log_code=False,
    ):
        pprint("Trying: %s" % (experiment.params,), "info")
        loss = objective_function(experiment.params["x"])
        experiment.log_metric("loss", loss, step=0)
        count += 1
        experiment.end()

    pprint("Optimizer job done! Completed %d experiments." % count, "good")


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

    includes = parsed_args.include if parsed_args.include else list(RESOURCES.keys())
    for item in parsed_args.exclude:
        if item in includes:
            includes.remove(item)
    # Handle subitems:
    for key in RESOURCES:
        for item in RESOURCES[key]:
            if item not in parsed_args.exclude and key in includes:
                includes.append(item)

    if "/" in parsed_args.COMET_PATH:
        if parsed_args.COMET_PATH.count("/") != 1:
            raise Exception("COMET_PATH should be WORKSPACE or WORKSPACE/PROJECT")
        workspace, project_name = parsed_args.COMET_PATH.split("/", 1)
    else:
        workspace, project_name = parsed_args.COMET_PATH, "smoke-tests"

    if workspace not in api.get_workspaces():
        raise Exception("workspace %r does not exist!" % workspace)

    pprint("Running cometx smoke tests...", "info")
    pprint("Using %s/%s on %s" % (workspace, project_name, comet_base_url), "info")

    if "experiment" in includes or any(
        value in includes for value in RESOURCES["experiment"]
    ):
        pprint("    Attempting to log experiment...", "info")
        project_data = api.get_project(workspace, project_name) or {}
        # Test Experiment
        key = test_experiment(
            includes,
            workspace,
            project_name,
            "test-%s" % (project_data.get("numberOfExperiments", 0) + 1),
        )
        experiment = api.get_experiment_by_key(key)

        # Verification
        if "metric" in includes:
            metric = experiment.get_metrics("loss")
            while len(metric) == 0 or "metricName" not in metric[0]:
                pprint("Waiting on metrics to finish processing...", "info")
                time.sleep(5)
                metric = experiment.get_metrics("loss")

            if "metricName" in metric[0] and metric[0]["metricValue"]:
                pprint("Successfully validated metric presence", "good")
            else:
                pprint("Something is wrong with logging metrics", "error")

        if "image" in includes:
            images = experiment.get_asset_list("image")

            if len(images) > 0:
                pprint("Successfully validated image presence", "good")
            else:
                pprint("Something is wrong with logging images", "error")

    if "panel" in includes:
        pprint("    Attempting to upload smoke-test panel...", "info")
        try:
            api.upload_panel_url(
                workspace,
                "https://raw.githubusercontent.com/comet-ml/comet-examples/master/panels/SmokeTest.py",
            )
            api.upload_panel_url(
                workspace,
                "https://raw.githubusercontent.com/comet-ml/comet-examples/master/panels/OptimizerAnalysis.py",
            )
        except Exception:
            pprint(
                "    Uploading panels is not supported in this backend. You need at least version 3.35.143",
                "error",
            )

    if "optimizer" in includes or any(
        value in includes for value in RESOURCES["optimizer"]
    ):
        pprint("    Attempting to run optimizer...", "info")
        os.environ["COMET_OPTIMIZER_URL"] = comet_base_url + "/optimizer/"
        test_optimizer(
            workspace=workspace,
            project_name=project_name,
        )
        pprint(
            "\nCompleted Optimizer test, you will need to check the Comet UI to ensure all the data has been correctly logged.\n",
            "good",
        )

    if "mpm" in includes or any(value in includes for value in RESOURCES["mpm"]):
        pprint("    Attempting to run mpm tests...", "info")
        test_mpm(api, workspace, project_name, nb_events=10, days=7)

        comet_mpm_ui_url = comet_base_url + f"/{workspace}#model-production-monitoring"
        pprint(
            f"\nCompleted MPM test, you will need to check the MPM UI ({comet_mpm_ui_url}) to validate the data has been logged, this can take up to 5 minutes.\n",
            "good",
        )

    pprint("All tests have completed", "info")


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
