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

from kangas import Audio, Curve, DataGrid, Image, Text, Video  # noqa

from ._version import __version__  # noqa
from .download_manager import DownloadManager  # noqa
from .utils import log_datagrid_to_experiment


class DataGrid(DataGrid):
    def log_to_experiment(self, experiment):
        """
        Special class for comet_ml to recognize and to allow:

        ```python
        >>> dg = DataGrid()
        >>> experiment.log(dg)
        """
        if not self.saved:
            self.save()

        log_datagrid_to_experiment(experiment, self.filename)
