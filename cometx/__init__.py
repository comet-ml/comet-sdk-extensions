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

from ._version import __version__  # noqa
from .api import API  # noqa
from .download_manager import DownloadManager  # noqa
