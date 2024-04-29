from IPython.core.magic import register_cell_magic

'''
from IPython.display import HTML, display
display(
    HTML(
        """
<style>
.p-Collapse {height: -webkit-fill-available;}
.p-Collapse-header {height: inherit;}
.p-Collapse.p-Accordion-child.p-Collapse-open.p-Accordion-child-active {
    height: auto;
}
</style>
"""
    )
)
'''


@register_cell_magic
def cometx(line, cell):
    path = line.split("/")
    experiment_id = ""
    if len(path) == 0:
        workspace = "dsblank"
        project_name = "comet-test"
    elif len(path) == 1:
        workspace = path[0]
        project_name = "general"
    elif len(path) == 2:
        workspace = path[0]
        project_name = path[1]
    elif len(path) == 3:
        workspace = path[0]
        project_name = path[1]
        experiment_id = path[2]
    if "def main(" not in cell:
        cell = "\n".join(["    %s\n" % line for line in cell.splitlines()])
        cell = """
def main(st):
    import comet_ml
    from comet_ml._ui import UI
    # Replace _st with ipywidgets
    class UI(UI):
        _st = st
        session_state = st.session_state
    comet_ml.ui = UI()
    del UI, comet_ml, st
    {cell}
""".format(
            cell=cell
        )
    code = """
import comet_ml

class API(comet_ml.API):
    def get_panel_project_name(self):
        return "{project_name}"
    def get_panel_workspace(self):
        return "{workspace}"
    def get_panel_experiments(self):
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
comet_ml.API = API
del comet_ml, API
## User code:
{cell}
## End user code
from cometx._ui import Streamlit
st = Streamlit()
st._run(main)
""".format(
        cell=cell,
        workspace=workspace,
        project_name=project_name,
        experiment_id=experiment_id,
    )
    get_ipython().run_cell(code)
    # print(code)
