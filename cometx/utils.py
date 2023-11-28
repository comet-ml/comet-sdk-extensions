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

import io
import json
import os
import sqlite3
import sys
import tempfile
import zipfile

from comet_ml.config import get_config
from comet_ml.utils import clean_string, get_root_url

import six


class ProgressBar:
    """
    A simple ASCII progress bar, showing a box for each item.
    Uses no control characters.
    """

    def __init__(self, sequence, description=None):
        """
        The sequence to iterate over. For best results,
        don't print during the iteration.
        """
        self.sequence = sequence
        if description:
            self.description = "%s " % description
        else:
            self.description = None

    def set_description(self, description):
        self.description = "%s " % description

    def __iter__(self):
        if self.description:
            print(self.description, end="")
        print("[", end="")
        sys.stdout.flush()
        for item in self.sequence:
            print("█", end="")
            sys.stdout.flush()
            yield item
        print("]")


def _input_user(prompt):
    # type: (str) -> str
    """Independent function to apply clean_string to all responses + make mocking easier"""
    return clean_string(six.moves.input(prompt))


def _input_user_yn(prompt):
    # type: (str) -> bool
    while True:
        response = _input_user(prompt).lower()
        if response.startswith("y") or response.startswith("n"):
            break
    return response.startswith("y")

def get_file_extension(file_path):
    if file_path is None:
        return None

    ext = os.path.splitext(file_path)[1]
    if not ext:
        return None

    # Get rid of the leading "."
    return ext[1::]


def display_invalid_api_key(api_key=None, cloud_url=None):
    print(
        "Invalid Comet API Key %r for %r"
        % (
            api_key or get_config("comet.api_key"),
            cloud_url
            or get_root_url(
                get_config("comet.url_override"),
            ),
        )
    )

def get_query_experiments(api, query_string, workspace, project_name):
    from comet_ml.query import (Environment, Metadata, Metric, Other, Parameter, Tag)

    env = {
        "Environment": Environment,
        "Metadata": Metadata,
        "Metric": Metric,
        "Other": Other,
        "Parameter": Parameter,
        "Tag": Tag,
    }
    query = eval(query_string, env)
    return api.query(workspace, project_name, query)
