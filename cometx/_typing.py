# -*- coding: utf-8 -*-
# *******************************************************
#   ____                     _               _
#  / ___|___  _ __ ___   ___| |_   _ __ ___ | |
# | |   / _ \| '_ ` _ \ / _ \ __| | '_ ` _ \| |
# | |__| (_) | | | | | |  __/ |_ _| | | | | | |
#  \____\___/|_| |_| |_|\___|\__(_)_| |_| |_|_|
#
#  Sign up for free at http://www.comet.ml
#  Copyright (C) 2015-2021 Comet ML INC
#  This file can not be copied and/or distributed without the express
#  permission of Comet ML Inc.
# *******************************************************

"""

This module contains useful types and mirror the typing module

"""

# isort: off

from typing import *  # noqa
from typing import IO, BinaryIO, Union  # noqa


class ValidFilePath(str):
    """This type help marking a file_path as existing on disk as checked by `is_valid_file_path`"""

    pass


class TemporaryFilePath(ValidFilePath):
    """This type help marking a file_path as valid on disk as checked by `is_valid_file_path`"""

    pass


UserText = Union[bytes, Text]  # noqa
MemoryUploadable = Union[IO, UserText]  # noqa
# With typing_extensions, we could use Literal["all"]
TensorflowInput = Union[int, str]  # noqa
Number = Union[int, float]
