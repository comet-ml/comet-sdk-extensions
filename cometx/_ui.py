import inspect
import io

import ipywidgets as widgets
import markdown
from IPython.display import HTML, clear_output, display

STYLE = """
<style>
table {width: -webkit-fill-available;}
</style>
"""


class SessionState(dict):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


class Streamlit:
    def __init__(self, parent=None):
        self._response = {}
        self._output = widgets.Output()
        self.session_state = SessionState()
        if parent is None:
            self._make_panel()
        else:
            self._parent = parent

    def _observe(self, widget, callback, names=None):
        widget.observe(callback, names=names)

    def _on_click(self, widget, callback):
        widget.on_click(callback)

    def _make_panel(self):
        self._top_level = widgets.VBox()
        self._parent = self._top_level

    def _clone(self, parent):
        app = Streamlit(parent)
        app._output = self._output
        app._response = self._response
        app.session_state = self.session_state
        app._function = self._function
        app._top_level = self._top_level
        return app

    def _make_key(self, widget_type, key):
        if key is None:
            calling_frame = inspect.getouterframes(inspect.currentframe())[2]
            key = calling_frame.lineno
            desc = "lineno"
        else:
            desc = "userkey"
        return "%s-%s-%s" % (widget_type, desc, key)

    def _append(self, widget):
        self._parent.children = self._parent.children + tuple([widget])

    # Widgets, replicates streamlit widgets

    def pyplot(self, figure):
        img_buf = io.BytesIO()
        figure.savefig(img_buf, format="png")
        img_buf.seek(0)
        image_data = img_buf.read()
        image = widgets.Image(
            value=image_data,
            format="png",
        )
        self._append(image)

    def image(self, data):
        # FIXME: ext, or type
        image = widgets.Image(
            value=data,
        )
        self._append(image)

    def write(self, data, unsafe_allow_html=False):
        if data.__class__.__name__ == "DataFrame":
            try:
                from ipydatagrid import DataGrid

                data = DataGrid(data)
            except ImportError:
                data = widgets.HTML(data)
        else:
            data = widgets.HTML(data)
        self._append(data)

    def selectbox(
        self,
        label,
        options,
        index=0,
        format_func=str,
        key=None,
        help=None,
        on_change=None,
        args=None,
        kwargs=None,
    ):
        key = self._make_key("selectbox", key)
        options = list(options)
        if len(options) == 0:
            label_options = [""]
            options = [None]

        label_options = [format_func(option) for option in options]
        index = self._response.get(key, index)
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
        )
        self._observe(
            widget,
            lambda results: self._rerun(key, results["owner"].index, on_change, args),
            names="value",
        )
        self._append(widgets.HTML("<font style='color:blue;'>%s</font>" % label))
        self._append(widget)
        self._response[key] = index
        return options[index]

    def multiselect(
        self,
        label,
        options,
        default=None,
        format_func=None,
        key=None,
        on_change=None,
        args=None,
        kwargs=None,
    ):
        # FIXME
        pass

    def plotly_chart(self, figure, use_container_width=False):
        # FIXME
        pass

    def button(self, label, key=None, help=None, on_click=None, args=None, kwargs=None):
        key = self._make_key("button", key)
        widget = widgets.Button(description=label)
        self._on_click(widget, lambda value: self._rerun(key, value, on_click, args))
        self._append(widget)
        retval = self._response.get(key, False)
        self._response[key] = False
        return retval

    def markdown(self, text, unsafe_allow_html=False):
        md = (
            """<div class="jp-RenderedHTMLCommon">"""
            + markdown.markdown(text)
            + """</div>"""
        )
        self._append(widgets.HTML(md))

    def text_input(
        self, label, value, key=None, on_change=None, args=None, kwargs=None
    ):
        # FIXME
        pass

    def checkbox(self, label, value, key=None, on_change=None, args=None, kwargs=None):
        # FIXME
        pass

    def columns(self, config):
        row = widgets.HBox()
        if isinstance(config, int):
            items = config
        else:
            items = len(config)
        row.children = tuple([widgets.VBox() for i in range(items)])
        self._append(row)
        return [self._clone(child) for child in row.children]

    def _run(self, function):
        self._function = function
        self._execute()

    def _rerun(self, key, value, callback, args):
        self._response[key] = value
        if callback:
            if args is None:
                callback()
            else:
                callback(*args)
        self._execute()

    def _execute(self):
        self._make_panel()
        with self._output:
            clear_output(wait=True)
            self._function(self)
            # This will only actually display the first time
            display(self._top_level, HTML(STYLE))
        clear_output(wait=True)
        display(self._output)
