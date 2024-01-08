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
import os
from urllib.parse import unquote

import wandb
from comet_ml.utils import makedirs

from ..utils import download_url, remove_extra_slashes


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
    ):
        self.api = wandb.Api()

        self.root = output if output is not None else os.getcwd()
        self.debug = debug
        self.flat = flat
        self.skip = skip
        self.force = force
        self.filename = filename
        self.asset_type = asset_type
        self.overwrite = overwrite

    def download(self, PATH):
        path = remove_extra_slashes(PATH)
        path_parts = path.split("/")
        if len(path_parts) == 3:
            workspace, project, experiment = path_parts
        elif len(path_parts) == 2:
            workspace, project = path_parts
            experiment = None
        elif len(path_parts) == 1:
            workspace = path_parts[0]
            project = None
            experiment = None
        else:
            raise Exception("invalid PATH: %r" % PATH)

        if project is None:
            projects = self.api.projects(workspace + "/" + project)
        else:
            projects = [project]

        # Download items:

        for project in projects:
            self.download_reports(workspace, project)

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
