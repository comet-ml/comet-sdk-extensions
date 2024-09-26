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
To generate the licence report.

cometx generate-license-report

"""

import argparse
import sys
from urllib.parse import urlparse

ADDITIONAL_ARGS = False


def get_parser_arguments(parser):
    parser.add_argument(
        "--debug", help="If given, allow debugging", default=False, action="store_true"
    )


def generate_license_report(parsed_args, remaining=None):
    # Called via `cometx generate-license-report ...`
    from comet_ml import API

    try:
        api = API()

        url = api.config["comet.url_override"]
        result = urlparse(url)
        netloc = result.netloc.split(".")[0] + "-admin"
        admin_url = "%s://%s/api/admin/generate-license-report" % (
            result.scheme,
            netloc,
        )
        response = api._client.get(
            admin_url, headers={"Authorization": api.api_key}, params={}
        )
        breakpoint()

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


def main(args):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    get_parser_arguments(parser)
    parsed_args = parser.parse_args(args)
    generate_license_report(parsed_args)


if __name__ == "__main__":
    # Called via `python -m cometx.cli.generate_license_report ...`
    main(sys.argv[1:])
