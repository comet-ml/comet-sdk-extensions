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

import os

# To keep comet_ml logger silent:
os.environ["COMET_LOGGING_CONSOLE"] = "CRITICAL"

from comet_ml import login  # noqa

from ._version import __version__  # noqa
from .api import API  # noqa


def upload_panel(name: str, workspace: str = None):
    # Upload well-known panel names
    api = API()
    workspace = workspace if workspace is not None else api.get_default_workspace()
    url = f"https://raw.githubusercontent.com/comet-ml/comet-examples/master/panels/{name}/{name}.py"
    return api.upload_panel_url(workspace, url)


upload_panel_name = upload_panel
