## app.py
# import micropip
# await micropip.install("markdown")

import inspect

import ipywidgets as widgets
import markdown
from IPython.display import clear_output, display


class SessionState(dict):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


class UI:
    def __init__(self, parent=None):
        self.response = {}
        self.output = widgets.Output()
        self.session_state = SessionState()
        self.session_state.sidebar_index = None
        if parent is None:
            self.make_panel()
        else:
            self.parent = parent

    def observe(self, widget, callback, names=None):
        widget.observe(callback, names=names)

    def on_click(self, widget, callback):
        widget.on_click(callback)

    @property
    def sidebar(self):
        return self.clone(self._sidebar)

    def make_panel(self):
        selected_index = self.session_state.sidebar_index
        self.top_level = widgets.HBox(
            [
                widgets.Accordion([widgets.VBox()], selected_index=selected_index),
                widgets.VBox(),
            ]
        )
        self._sidebar = self.top_level.children[0].children[0]
        self.observe(
            self.top_level.children[0], self.set_sidebar, names="_property_lock"
        )
        self.parent = self.top_level.children[1]

    def set_sidebar(self, results):
        self.session_state.sidebar_index = results["owner"].selected_index

    def clone(self, parent):
        app = UI(parent)
        app.output = self.output
        app.response = self.response
        app.session_state = self.session_state
        app.function = self.function
        app.top_level = self.top_level
        app._sidebar = self._sidebar
        return app

    def make_key(self, widget_type, key):
        if key is None:
            calling_frame = inspect.getouterframes(inspect.currentframe())[2]
            key = calling_frame.lineno
            desc = "lineno"
        else:
            desc = "userkey"
        return "%s-%s-%s" % (widget_type, desc, key)

    def selectbox(
        self,
        label,
        options,
        index=0,
        format_func=None,
        key=None,
        help=None,
        on_change=None,
        args=None,
        kwargs=None,
    ):
        key = self.make_key("selectbox", key)
        options = list(options)
        if len(options) == 0:
            label_options = [""]
            options = [None]
        elif format_func is not None:
            label_options = [format_func(option) for option in options]
        else:
            label_options = options
        index = self.response.get(key, index)
        if index < len(label_options):
            value = label_options[index]
        else:
            value = label_options[0]
            index = 0
        widget = widgets.Dropdown(
            style={
                "description_width": "initial",
                "width": "initial",
            },
            options=label_options,
            value=value,
            # description="<font style='color:blue;'>%s</font>:" % label,
        )
        self.observe(
            widget,
            lambda results: self.rerun(key, results["owner"].index, on_change, args),
            names="value",
        )
        self.append(widgets.HTML("<font style='color:blue;'>%s</font>:" % label))
        self.append(widget)
        self.response[key] = index
        return options[index]

    def button(self, label, key=None, help=None, on_click=None, args=None, kwargs=None):
        key = self.make_key("button", key)
        widget = widgets.Button(description=label)
        self.on_click(widget, lambda value: self.rerun(key, value, on_click, args))
        self.append(widget)
        retval = self.response.get(key, False)
        self.response[key] = False
        return retval

    def title(self, body):
        self.append(widgets.HTML(body))

    def append(self, widget):
        self.parent.children = self.parent.children + tuple([widget])

    def write(self, *args, color=None, **kwargs):
        def strip(s):
            lines = []
            for line in s.splitlines():
                lines.append(line.strip())
            return "\n".join(lines).strip()

        if "raw" not in kwargs:
            args = " ".join([strip(str(arg)) for arg in args])
            if color is not None:
                args = '<p style="color:{color}">{args}</p>'.format(
                    color=color, args=args
                )

            # HTML widget surrounds items in a div with different CSS, widget-html-content
            md = (
                """<div class="jp-RenderedHTMLCommon">"""
                + markdown.markdown(args)
                + """</div>"""
            )
            self.append(widgets.HTML(md))
        else:
            self.append(widgets.HTML("".join(args)))

    def success(self, *args, **kwargs):
        self.write(*args, color="green", **kwargs)

    def warning(self, *args, **kwargs):
        self.write(*args, color="red", **kwargs)

    def beta_columns(self, config):
        row = widgets.HBox()
        if isinstance(config, int):
            items = config
        else:
            items = len(config)
        row.children = tuple([widgets.VBox() for i in range(items)])
        self.append(row)
        return [self.clone(child) for child in row.children]

    def run(self, function):
        self.function = function
        self.execute()

    def rerun(self, key, value, callback, args):
        self.response[key] = value
        if callback:
            if args is None:
                callback()
            else:
                callback(*args)
        self.execute()

    def execute(self):
        clear_output(wait=True)
        self.make_panel()
        with self.output:
            clear_output(wait=True)
            self.function(self)
            if len(self._sidebar.children) == 0:
                # remove sidebar, nothing in it
                self.top_level.children = tuple([self.top_level.children[1]])
            display(self.top_level)
        display(self.output)
