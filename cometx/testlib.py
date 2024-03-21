# -*- coding: utf-8 -*-
# ****************************************
#                               __
#    _________  ____ ___  ___  / /__  __
#   / ___/ __ \/ __ `__ \/ _ \/ __/ |/ /
#  / /__/ /_/ / / / / / /  __/ /_ >   <
#  \___/\____/_/ /_/ /_/\___/\__//_/|_/
#
#        Copyright (c) 2024 Cometx
#  Development Team. All rights reserved.
# ****************************************

import json

from comet_ml import Experiment
from comet_ml.comet import Streamer
from comet_ml.connection import (
    RestServerConnection,
    WebSocketConnection,
    get_backend_address,
)
from comet_ml.console import StdLogger
from comet_ml.experiment import BaseExperiment
from comet_ml.feature_toggles import USE_HTTP_MESSAGES, FeatureToggles
from comet_ml.messages import BaseMessage

FLUSH_INITIAL_DATA_LOGGER_TIMEOUT = 10

some_key = "some key"
some_value = "some value"
some_api_key = "some api key"
some_ws_address = "ws://localhost:1234"
some_run_id = "some run id"
some_project_id = "some project id"
some_project_name = "some  project name"
some_experiment_id = "some experiment id"
some_workspace_id = "some-workspace-id"
some_focus_url = "www.someurl.com?focus="


class DummyStdLogger(StdLogger):
    def __init__(self, *args, **kwargs):
        super(DummyStdLogger, self).__init__(*args, **kwargs)


class DummyStreamer(Streamer):
    def __init__(self, api_key, run_id, project_id, use_http_messages=False):
        self.messages = []  # type: List[BaseMessage]
        self.closed = False
        self.api_key = api_key
        self.run_id = run_id
        self.project_id = project_id
        self.error_reported = False
        self.error_message = None
        self.has_crashed = False
        self.use_http_messages = use_http_messages
        self._counter = 0

    def put_message_in_q(self, message: BaseMessage):
        message.message_id = self._counter
        self.messages.append(message)

    def get_last_msg(self) -> BaseMessage:
        return self.messages[-1]

    def getn(self, n):
        return self.messages[-n:]

    def get_all(self):
        return self.messages

    def get_one_before_last(self):
        return self.getn(2)[0]

    def has_connection_to_server(self):
        return True

    def flush(self):
        return True

    def wait_for_finish(self, **kwargs):
        return True

    def has_upload_failed(self):
        return False

    def clean(self):
        self.messages = []

    def close(self):
        self.closed = True

    def _report_experiment_error(self, message: str, has_crashed: bool = False):
        self.error_reported = True
        self.error_message = message
        self.has_crashed = has_crashed

    def __str__(self):
        return "DummyStreamer()"

    def __repr__(self):
        return "DummyStreamer()"


class DummyWsConnection(WebSocketConnection):
    def __init__(self, *args, **kwargs):
        self.address = None

    def wait_for_connection(self):
        pass

    def is_connected(self):
        return True

    def __repr__(self):
        return "DummyWsConnection"

    def wait_for_finish(self, *args, **kwargs):
        return True


class DummyHeartBeatThread(object):
    def close(self):
        return None

    def join(self, timeout):
        return True


def experiment_builder(
    api_key=some_api_key,
    cls=Experiment,
    streamer=None,
    ws_url="ws://localhost/",
    feature_toggles=None,
    allow_report=False,
    upload_web_asset_url_prefix="",
    upload_web_image_url_prefix="",
    upload_api_asset_url_prefix="",
    upload_api_image_url_prefix="",
    log_git_metadata=False,
    log_git_patch=False,
    log_env_cpu=False,
    **kwargs
):
    class _TestingExperiment(cls):
        def _setup_http_handler(self):
            self.http_handler = None

        def _setup_streamer(self, *args, **kwargs):
            if streamer is None:
                self.streamer = DummyStreamer(
                    api_key=some_api_key, run_id=some_run_id, project_id=some_project_id
                )
            else:
                self.streamer = streamer

            if feature_toggles is None:
                self.feature_toggles = FeatureToggles({}, self.config)
            else:
                self.feature_toggles = FeatureToggles(feature_toggles, self.config)

            self.upload_web_asset_url_prefix = upload_web_asset_url_prefix
            self.upload_web_image_url_prefix = upload_web_image_url_prefix
            self.upload_api_asset_url_prefix = upload_api_asset_url_prefix
            self.upload_api_image_url_prefix = upload_api_image_url_prefix

            # Create a Connection for the cases where we need to test the reports
            if allow_report:
                self.connection = RestServerConnection(
                    self.api_key,
                    self.id,
                    get_backend_address(),
                    self.config["comet.timeout.http"],
                    verify_tls=True,
                )

            self._heartbeat_thread = DummyHeartBeatThread()

            return True

        def _mark_as_started(self):
            pass

        def _mark_as_ended(self):
            pass

        def add_tag(self, *args, **kwargs):
            return BaseExperiment.add_tag(self, *args, **kwargs)

        def add_tags(self, *args, **kwargs):
            return BaseExperiment.add_tags(self, *args, **kwargs)

        def _report(self, *args, **kwargs):
            if not allow_report:
                return None

            return super(_TestingExperiment, self)._report(*args, **kwargs)

        def _register_callback_remotely(self, *args, **kwargs):
            pass

        def send_notification(self, title, status=None, additional_data=None):
            pass

        def _check_experiment_throttled(self):
            return False

    return _TestingExperiment(
        api_key,
        log_git_metadata=log_git_metadata,
        log_git_patch=log_git_patch,
        log_env_cpu=log_env_cpu,
        **kwargs
    )


def build_experiment(
    flush_initial_data_logger_timeout=FLUSH_INITIAL_DATA_LOGGER_TIMEOUT,
    api_key=some_api_key,
    run_id=some_run_id,
    project_id=some_project_id,
    auto_output_logging=None,
    feature_toggles=None,
    **kwargs
):
    # this line is used for source code testing, don't remove this comment
    use_http_messages = False
    if feature_toggles is not None:
        if feature_toggles.get(USE_HTTP_MESSAGES) is True:
            use_http_messages = True

    streamer = DummyStreamer(
        api_key=api_key,
        run_id=run_id,
        project_id=project_id,
        use_http_messages=use_http_messages,
    )
    if auto_output_logging is None:
        auto_output_logging = "simple"
    kwargs["log_env_cpu"] = kwargs.get("log_env_cpu", False)
    kwargs["log_env_gpu"] = kwargs.get("log_env_gpu", False)
    kwargs["log_env_network"] = kwargs.get("log_env_network", False)
    kwargs["log_env_disk"] = kwargs.get("log_env_disk", False)

    experiment = experiment_builder(
        api_key=api_key,
        streamer=streamer,
        auto_output_logging=auto_output_logging,
        feature_toggles=feature_toggles,
        **kwargs
    )

    # flush initial data logger thread
    experiment._flush_initial_data_logger(flush_initial_data_logger_timeout)
    experiment.streamer.clean()
    return experiment


class TestExperiment:
    """
    An Experiment class for use in test frameworks.

    The methods beginning with "meta" are not part of an experiment,
    but for use in testing.

    Example:

    ```
    >>> from cometx.testlib import TestExperiment
    >>> experiment = TestExperiment()
    >>> experiment.log_other("Name", "my-new-name")
    >>> experiment.meta_get_message_types()
    ['stderr', 'stdout', 'log_other']
    >>> assert experiment.meta_get_messages(mtype="log_other")[0]["log_other"]["key"] == "Name"
    >>> assert experiment.meta_get_messages(mtype="log_other")[0]["log_other"]["value"] == "my-new-name"
    ```

    Each message type has its own structure.
    """

    def __init__(self, *args, **kwargs):
        self._experiment = build_experiment(
            FLUSH_INITIAL_DATA_LOGGER_TIMEOUT, *args, **kwargs
        )

    def __getattr__(self, attr):
        return getattr(self._experiment, attr)

    def _get_all_messages(self, messages, mtype):
        found_messages = []
        for message in messages:
            if getattr(message, mtype, None):
                found_messages.append(message)
        return found_messages

    def meta_get_message_types(self):
        """
        Get all of the messages so far.

        Returns a list of strings representing message tupes.
        """
        retval = set()
        for message in self._experiment.streamer.messages:
            keys = set(json.loads(message.to_json()).keys())
            keys = keys - set(["local_timestamp", "message_id"])
            retval.update(keys)
        return list(retval)

    def meta_get_messages(self, mtype=None):
        """
        Get all of the messages logged so far, optionally of a specific
        type.

        Args:
            mtype: (string, optional) a message type

        Returns list of message dicts

        See also: TestExperiment.meta_get_message_types()
        """
        if mtype is not None:
            return [
                json.loads(message.to_json())
                for message in self._get_all_messages(
                    self._experiment.streamer.messages, mtype
                )
            ]
        else:
            return [
                json.loads(message.to_json())
                for message in self._experiment.streamer.messages
            ]
