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

import json
import os
import tempfile
import time
import uuid
import zipfile


def int_to_string(number, alphabet, padding=None) -> str:
    """
    Convert a number to a string, using the given alphabet.

    The output has the most significant digit first.
    """
    output = ""
    alpha_len = len(alphabet)
    while number:
        number, digit = divmod(number, alpha_len)
        output += alphabet[digit]
    if padding:
        remainder = max(padding - len(output), 0)
        output = output + alphabet[0] * remainder
    return output[::-1]


def get_uuid(length):
    u = uuid.uuid4()
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return int_to_string(u.int, alphabet, length)


def create_panel_zip(name, code):
    u = get_uuid(25)
    template = {
        "templateName": name,
        "code": {
            "code": "",
            "css": "",
            "description": "",
            "html": "",
            "defaultConfig": "",
            "internalResources": [],
            "userResources": [],
            "pyCode": code.lstrip(),
            "type": "py",
            "pyConfig": "{}",
        },
        "createdAt": int(time.time() * 1000),
        "thumbnailName": "template-thumbnail-%s" % u,
        "editable": True,
    }
    tmpdirname = tempfile.mkdtemp()
    zip_filename = os.path.join(tmpdirname, "panel-%s.zip" % u)
    with zipfile.ZipFile(zip_filename, "w") as zip_fp:
        zip_fp.writestr("tempVisualizationTemplate.json", json.dumps(template))
        # Note: can also add a thumbnail 100 x 66 jpg here
    return zip_filename
