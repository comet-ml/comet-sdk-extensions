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

from IPython.core.magic import register_cell_magic


@register_cell_magic
def cometx(line, cell):
    path = line.split("/")
    if len(path) == 2:
        workspace = path[0]
        project_name = path[1]
        experiment_key = ""
    elif len(path) == 3:
        workspace = path[0]
        project_name = path[1]
        experiment_key = path[2]
    else:
        raise Exception(
            "Need to provide WORKSPACE/PROJECT or WORKSPACE/PROJECT/EXPERIMENT to %%cometx"
        )

    if "def main(" not in cell:
        cell = "\n".join(["    %s\n" % line for line in cell.splitlines()])
        cell = """
def main(st):
    import comet_ml
    from comet_ml._ui import UI

    class API(comet_ml.API):
        def get_panel_project_name(self):
            return "{project_name}"
        def get_panel_workspace(self):
            return "{workspace}"
        def get_panel_experiments(self):
            if "{experiment_key}":
                return [self.get_experiment("{workspace}", "{project_name}", "{experiment_key}")]
            else:
                return self.get_experiments("{workspace}", "{project_name}")
        def get_panel_experiment_keys(self):
            return [e.id for e in self.get_panel_experiments()]
        def get_panel_metrics_names(self):
            return sorted(
                [
                    name
                    for name in self._get_metrics_name(
                        "{workspace}",
                        "{project_name}",
                    )
                    if not name.startswith("sys.")
                ]
            )
    # Replace API with new API
    comet_ml.API = API
    # Replace _st with ipywidgets
    class UI(UI):
        _st = st
        session_state = st.session_state
    comet_ml.ui = UI()
    del UI, comet_ml, st, API
    {cell}
    import comet_ml
    cols = comet_ml.ui.columns(2)
    cols[-1].button("Deploy to Comet...")
""".format(
            cell=cell,
            workspace=workspace,
            project_name=project_name,
            experiment_key=experiment_key,
        )
    code = """
## User code:
{cell}
## End user code
from cometx._ui import Streamlit
st = Streamlit()
st._run(main)
""".format(
        cell=cell
    )
    get_ipython().run_cell(code)
    # print(code)
