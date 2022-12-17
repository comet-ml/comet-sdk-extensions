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
#  Copyright (c) 2022 Cometx Development
#      Team. All rights reserved.
# ****************************************
"""
Examples:

To download experiments or experiment resources:

$ cometx download [RESOURCE ...] [FLAGS ...]
$ cometx download WORKSPACE [RESOURCE ...] [FLAGS ...]
$ cometx download WORKSPACE/PROJECT [RESOURCE ...] [FLAGS ...]
$ cometx download WORKSPACE/PROJECT/EXPERIMENT-KEY [RESOURCE ...] [FLAGS ...]

Where [RESOURCE ...] is zero or more of the following names:

* run - alias for: code, git, output, graph, and requirements
* system
* others
* parameters
* metadata
* metrics
* assets
* html
* project - alias for: project_notes, project_metadata

To download artifacts:

$ cometx download WORKSPACE/artifacts/NAME [FLAGS ...]
$ cometx download WORKSPACE/artifacts/NAME/VERSION-OR-ALIAS [FLAGS ...]

To download models from the registry:

$ cometx download WORKSPACE/model-registry/NAME [FLAGS ...]
$ cometx download WORKSPACE/model-registry/NAME/VERSION-OR-STAGE [FLAGS ...]

Where [FLAGS ...] is zero or more of the following:

* `--list` - use to list available workspaces, projects, experiments,
    artifacts, or models
* `--output` - download resources to folder other than current one
* `--flat` - don't use the normal hiearchy for downloaded items
* `--use-name` - use experiment names for folders and listings
* `--ignore` - don't download the following resources (use one or more
    RESOURCE names from above)
* `--asset-type` - asset type to match, or leave off to match all
* `--filename` - filename to match, or leave off to match all
* `--overwrite` - overwrite any existing files
* `--force` - don't ask to download, just do it
* `--help` - this message

"""

import argparse
import sys

from comet_ml.exceptions import InvalidRestAPIKey

from cometx import DownloadManager
from cometx.utils import display_invalid_api_key

ADDITIONAL_ARGS = False


def get_parser_arguments(parser):
    parser.add_argument(
        "COMET_PATH",
        help=(
            "The Comet identifier, such as 'WORKSPACE', 'WORKSPACE/PROJECT', or "
            + "'WORKSPACE/PROJECT/EXPERIMENT'. Leave empty for all workspaces."
        ),
        nargs="?",
    )
    parser.add_argument(
        "RESOURCE",
        help=(
            "Resource(s) to include in download. For experiments, any of: system, run, code, git, "
            + "output, requirements, others, parameters, metadata, metrics, output, assets, "
            + "project, project_notes, or project_metadata."
        ),
        nargs="*",
        default=[],
    )
    parser.add_argument(
        "-i", "--ignore", help="Resource(s) to ignore.", nargs="+", default=[]
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output directory for downloads.",
        type=str,
    )
    parser.add_argument(
        "-u",
        "--use-name",
        help="Use experiment names for experiment folders and listings",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-l",
        "--list",
        help="List the items at this level (workspace, project, experiment, artifacts, or model-registry) rather than download.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--flat",
        help="Download the files without subfolders.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-f",
        "--force",
        help="Do not query the user; answer `yes` for any questions",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--filename",
        help="Only get resources ending with this",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--asset-type",
        help="Only get assets with this type",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--overwrite",
        help="Overwrite any existing files",
        type=bool,
        default=False,
    )


def download(parsed_args, remaining=None):
    try:
        downloader = DownloadManager()
    except ValueError:
        display_invalid_api_key()
        return

    try:
        downloader.download(
            comet_path=parsed_args.COMET_PATH,
            include=parsed_args.RESOURCE,
            ignore=parsed_args.ignore,
            output=parsed_args.output,
            use_name=parsed_args.use_name,
            list_items=parsed_args.list,
            flat=parsed_args.flat,
            force=parsed_args.force,
            filename=parsed_args.filename,
            asset_type=parsed_args.asset_type,
            overwrite=parsed_args.overwrite,
        )
    except InvalidRestAPIKey:
        display_invalid_api_key()
    except Exception as exc:
        print("Download aborted: %s" % str(exc))
    except KeyboardInterrupt:
        print("User canceled download by keyboard interrupt")


def main(args):
    # Called via `cometx download ...`
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    get_parser_arguments(parser)
    parsed_args = parser.parse_args(args)

    download(parsed_args)


if __name__ == "__main__":
    # Called via `python -m cometx.cli.download ...`
    # Called via `cometx download ...`
    main(sys.argv[1:])
