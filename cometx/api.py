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

from comet_ml import API


class API(API):
    def get_panels(self, workspace):
        """
        Get a list of all panels in a workspace.

        The return value has the following structure:

        ```json
        [
            {
                "templateId": "SzUYHmX7hnR7KrLzU1tBrHilq",
                "owner": "owner",
                "teamId": "owner-default",
                "templateName": "Panel Name",
                "queryBuilderId": "",
                "scopeType": "PUBLIC",
                "revisionId": 1596673911412,
                "createdAt": 1584445331784
            }, ...
            ]
        ```
        """
        results = self._client.get_from_endpoint(
            "code-panel/get-all", {"workspace": workspace}
        )
        return results["codePanelTemplateRows"]

    def get_panel(self, template_id=None, instance_id=None):
        """
        Get a panel JSON given a panel's instance or template id.

        The result has the following structure:
        ```json
        {
            "templateId": "DyfpvKGZJvrtY1jjsYuMmLgz5",
            "owner": "owner",
            "teamId": "owner-default",
            "templateName": "Panel Name",
            "queryBuilderId": "",
            "code": {
                "code": "// JavaScript Code",
                "css": "/** CSS **/",
                "description": "Panel Description",
                "html": "<div id=\"chart-mount\"></div>",
                "defaultConfig": "\"\"",
                "internalResources": [
                    {
                        "name": "Comet SDK",
                        "version": "latest",
                        "enabled": true
                    },
                    {
                        "name": "Plotly.js",
                        "version": "1.50.1",
                        "enabled": true
                    }
                ],
                "userResources": [],
                "pyCode": "## Python Code",
                "type": "py",
                "pyConfig": ""
            },
            "rank": {
                "templateId": "DyfpvKGZJvrtY1jjsYuMmLgz5",
                "voteCount": 0,
                "userVoteType": "NOVOTE"
            },
            "scopeType": "PRIVATE",
            "revisionId": 1642709054245,
            "createdAt": 1642709054465,
            "thumbnailName": "template-thumbnail-DyfpvKGZJvrtY1jjsYuMmLgz5",
            "editable": true
        }
        ```
        """
        if template_id:
            results = self._client.get_from_endpoint(
                "code-panel/download", {"templateId": template_id}
            )
        elif instance_id:
            results = self._client.get_from_endpoint(
                "code-panel/download", {"instanceId": instance_id}
            )
        return results

    def download_panel_zip(self, template_id, filename=None):
        """
        Download a panel zip file.
        """
        results = self._client.get_from_endpoint(
            f"template/{template_id}/download", {}, return_type="binary"
        )
        filename = filename if filename else f"panel-{template_id}.zip"
        with open(filename, "wb") as fp:
            fp.write(results)
        return filename

    def upload_panel_zip(self, workspace_id, filename):
        """
        Upload a panel zip file to a workspace.
        """
        results = self._client.post_from_endpoint(
            "write/template/upload", {"teamId": workspace_id}, files={"file": filename}
        )
        return results

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
