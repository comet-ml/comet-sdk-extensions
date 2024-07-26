# -*- coding: utf-8 -*-
# ****************************************
#                              __
#   _________  ____ ___  ___  / /__  __
#  / ___/ __ \/ __ `__ \/ _ \/ __/ |/_/
# / /__/ /_/ / / / / / /  __/ /__>  <
# \___/\____/_/ /_/ /_/\___/\__/_/|_|
#
#
#  Copyright (c) 2023 Cometx Development
#      Team. All rights reserved.
# ****************************************

from typing import Any, Dict, List

from comet_ml import API

from .panel_utils import create_panel_zip


class API(API):
    def get_panels(self, workspace: str) -> List[Dict[str, Any]]:
        """
        Get the metadata for all panels in a workspace.

        Args:
            workspace (str): the name of the workspace

        Returns: a list of dictionaries representing the panel
            metadata.

        Example:
        ```python linenums="1"
        from cometx import API

        api = API()
        panels = api.get_panels("my-workspace-name")
        ```
        The structure of a panel metadata:
        ```json
        {
         'templateId': '1234',
         'owner': 'OWNER',
         'teamId': 'OWNER-default',
         'templateName': 'PANEL NAME',
         'queryBuilderId': '',
         'scopeType': 'PRIVATE',
         'revisionId': 1721739799515,
         'createdAt': 1721739799581
        }
        ```
        """
        results = self._client.get_from_endpoint(
            "code-panel/get-all", {"workspace": workspace}
        )
        return results["codePanelTemplateRows"]

    def get_panel(self, panel_id: str) -> Dict[str, Any]:
        """
        Get the panel data given the panel's ID.

        Args:
            panel_id (str): the panel id (also called templateId)

        Returns: a dictionary of panel data

        Example:
        ```python linenums="1"
        from cometx import API

        api = API()
        panel = api.get_panel("1234")
        ```
        """
        results = self._client.get_from_endpoint(
            "code-panel/download", {"templateId": panel_id}
        )
        return results

    def get_panel_code(self, panel_id: str) -> str:
        """
        Given a panel ID, return the active code (may be JavaScript or Python).

        Args:
            panel_id (str): the panel id (also called templateId)

        Example:
        ```python linenums="1"
        from cometx import API

        api = API()
        panels = api.get_panel_code("1234")
        ```
        """
        metadata = self.get_panel(panel_id)
        if metadata["code"]["type"] == "py":
            return metadata["code"]["pyCode"]
        else:
            return metadata["code"]["code"]

    def download_panel_zip(self, panel_id, filename=None):
        """
        Given a panel ID, download the associationed panel as a zip file.

        Args:
            panel_id (str): the panel ID
            filename (str): optional, the path/filename of where to save
                the panel

        Example:
        ```python linenums="1"
        from cometx import API

        api = API()
        filename = api.download_panel_zip("1234")
        ```
        """
        results = self._client.get_from_endpoint(
            f"template/{panel_id}/download", {}, return_type="binary"
        )
        filename = filename if filename else f"panel-{panel_id}.zip"
        with open(filename, "wb") as fp:
            fp.write(results)
        return filename

    def upload_panel_code(self, workspace: str, panel_name: str, code: str) -> None:
        """
        Upload Python code as a panel in a workspace.

        Args:
            workspace (str): the workspace to place the panel into
            panel_name (str): the name of the panel
            code (str): the code to turn into a panel

        Example:
        ```python linenums="1"
        from cometx.api import API

        api = API()

        code = '''
        from comet_ml import ui
        ui.display("Hello, world, from a script!")
        '''
        api.upload_panel_code("my-workspace", "My Python Script", code)
        ```
        """
        filename = create_panel_zip(panel_name, code)
        self.upload_panel_zip(workspace, filename)

    def upload_panel_zip(self, workspace: str, filename: str) -> Dict[str, str]:
        """
        Upload a panel zip file to a workspace.

        Args:
            workspace (str): the workspace to place the panel into
            filename (str): the name of the panel zip to upload

        Returns: dictionary of results

        Example:
        ```python linenums="1"
        from cometx import API

        api = API()
        panels = api.upload_panel_zip("my-workspace", "panel-1234.zip")
        ```
        """
        params = {"teamName": workspace}
        payload = {}
        with open(filename, "rb") as fp:
            files = {"file": (filename, fp)}
            results = self._client.post_from_endpoint(
                "write/template/upload",
                payload=payload,
                params=params,
                files=files,
            )
        return results.json()

    def log_pr_curves(
        self, experiment, y_true, y_predicted, labels=None, overwrite=False, step=None
    ):
        """
        Log a Precision/Recall curve for each class/column to the given experiment.

        Args:
            experiment: the experiment to log the curves to
            y_true: a list of lists of binary truth (where 1 means that column's class is present)
            y_predicted: a list of list of probabilities of predictions (0 to 1) for each output
            labels (optional): a list of strings (class names)
            overwrite (optional): whether to overwrite previously-logged curves
            step: (optional, by highly encouraged) the step in the training process
        """
        try:
            import numpy as np
            from sklearn.metrics import precision_recall_curve
        except ImportError:
            raise Exception(
                "Experiment.log_pr_curve() requires numpy and sklearn"
            ) from None

        y_true = np.array(y_true)
        y_predicted = np.array(y_predicted)

        if labels is None:
            labels = [("Class %s" % i) for i in range(len(y_true[0]))]

        results = []
        for i in range(len(labels)):
            y, x, _ = precision_recall_curve(y_true[:, i], y_predicted[:, i])

            result = experiment.log_curve(
                name=labels[i],
                x=x,
                y=y,
                overwrite=overwrite,
                step=step,
            )
            results.append(result)
        return results
