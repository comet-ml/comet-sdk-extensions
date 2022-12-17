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


def get_comet_type(asset_type):
    """
    Mapping from datagrid Asset type to Comet
    asset type.
    """
    if asset_type == "Text":
        return "text-sample"
    else:
        # Audio, Image, Video, Curve, etc.
        return asset_type.lower()


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


def log_datagrid_to_experiment(experiment, filename, output=None):
    """
    Create the SQLite database, zip it, and log it to
    an experiment.

    Args:

    * filename - (str) the name of the datagrid file
    * output - (optional, str) the name of the output dg
    """
    suffix = ".datagrid"

    if output is None:
        output = tempfile.NamedTemporaryFile(suffix=suffix, delete=False).name

    conn = sqlite3.connect(output)
    cur = conn.cursor()
    cur.execute("ATTACH DATABASE '{filename}' as original;".format(filename=filename))
    cur.execute("CREATE TABLE datagrid AS SELECT * from original.datagrid;")
    cur.execute("CREATE TABLE metadata AS SELECT * from original.metadata;")
    conn.commit()

    zip_file = tempfile.NamedTemporaryFile(suffix=".dgz", delete=False).name

    try:
        # zlib may not be installed
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(output)
    except Exception:
        # if not, we'll just package it up as if it were:
        with zipfile.ZipFile(zip_file, "w") as zipf:
            zipf.write(output)

    results = experiment._log_asset(zip_file, file_name=filename, asset_type="datagrid")

    # Log all of the assets:
    rows = conn.execute(
        "SELECT asset_id, asset_type, asset_data, asset_metadata from original.assets;"
    )
    for row in rows.fetchall():
        # FIXME: make sure asset is not already logged
        asset_id, asset_type, asset_data, asset_metadata = row
        metadata = json.loads(asset_metadata)
        if isinstance(asset_data, str):
            binary_io = io.StringIO(asset_data)
        else:
            binary_io = io.BytesIO(asset_data)
        file_name = metadata.get("filename", "%s-%s" % (asset_type, asset_id))
        comet_type = get_comet_type(asset_type)
        experiment._log_asset(
            binary_io,
            file_name=file_name,
            copy_to_tmp=False,
            asset_type=comet_type,
            asset_id=asset_id,
        )
    return results


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
