from IPython.core.magic import register_cell_magic
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
    if "def show(" not in cell:
        cell = "\n".join(["    %s\n" % line for line in cell.splitlines()])
        cell = "def show(st):\n" + cell
    code = """
import comet_ml
from cometx._ui import UI
class API(comet_ml.API):
    def get_panel_experiment_names(self):
        if not hasattr(self, "cache"):
            if "{experiment_id}" == "":
                self.cache = self.get_experiments("{workspace}", "{project_name}")[:100]
            else:
                self.cache = [self.get_experiment_by_id("{experiment_id}")]
        return [e.name for e in self.cache]

    def get_panel_experiments(self):
        if not hasattr(self, "cache"):
            if "{experiment_id}" == "":
                self.cache = self.get_experiments("{workspace}", "{project_name}")
            else:
                self.cache = [self.get_experiment_by_id("{experiment_id}")]
        return [e.id for e in self.cache]

    def get_experiment_by_name(self, experiment_name):
        return [e for e in self.cache if e.name == experiment_name][0]
comet_ml.ui = UI()
## User code:
{cell}
## End user code
comet_ml.ui.run(show)""".format(
        cell=cell,
        workspace=workspace,
        project_name=project_name,
        experiment_id=experiment_id,
    )
    get_ipython().run_cell(code)
    # print(code)
