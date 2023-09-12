# -*- coding: utf-8 -*-
# ****************************************
#                              __
#   _________  ____ ___  ___  / /__  __
#  / ___/ __ \/ __ `__ \/ _ \/ __/ |/_/
# / /__/ /_/ / / / / / /  __/ /__>  <
# \___/\____/_/ /_/ /_/\___/\__/_/|_|
#
#
#  Copyright (c) 2022 Cometx Development
#      Team. All rights reserved.
# ****************************************

import math
import json
import tempfile
import os

from collections import defaultdict

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image, ImageDraw = None, None

## Randomize large files

def merge_files(temp_files, filename_out):
    with open(filename_out, "w") as fp_out:
        for temp_file in temp_files:
            with open(temp_file.name) as fp:
                line = fp.readline()
                while line:
                    fp_out.write(line)
                    line = fp.readline()

def shuffle(filename_in, filename_out, memory_limit, file_split_count, 
            depth=0, debug=False):
    if os.path.getsize(filename_in) < memory_limit:
        if debug: print(" " * depth, f"Level {depth + 1}",
            "Shuffle in memory...")
        shuffle_in_memory(filename_in, filename_out)
    else:
        if debug: print(
            " " * depth, f"Level {depth + 1}",
            f"{os.path.getsize(filename_in)} is too big;",
            f"Split into {file_split_count} files..."
        )
        # Split the big file into smaller files
        temp_files = [tempfile.NamedTemporaryFile('w+', delete=False)
                      for i in range(file_split_count)]
        for line in open(filename_in):
            random_index = random.randint(0, len(temp_files) - 1)
            temp_files[random_index].write(line)

        # Now we shuffle each smaller file
        for temp_file in temp_files:
            temp_file.close()
            shuffle(temp_file.name, temp_file.name, memory_limit, 
                    file_split_count, depth+1, debug)

        # And merge back in place of the original
        if debug: print(" " * depth, f"Level {depth + 1}", 
            "Merge files...")
        merge_files(temp_files, filename_out)

## 3D Graphics functions

def identity():
    """
    Return matrix for identity (no transforms).
    """
    return [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]

def rotate_x(angle):
    """
    Return transform matrix for rotation around x axis.
    """
    radians = angle * math.pi / 180
    return [
        [1, 0, 0, 0],
        [0, math.cos(radians), -math.sin(radians), 0],
        [0, math.sin(radians), math.cos(radians), 0],
        [0, 0, 0, 1]
    ]

def rotate_y(angle):
    """
    Return transform matrix for rotation around y axis.
    """
    radians = angle * math.pi / 180
    return [
        [math.cos(radians), 0, math.sin(radians), 0],
        [0, 1, 0, 0],
        [-math.sin(radians), 0, math.cos(radians), 0],
        [0, 0, 0, 1]
    ]

def rotate_z(angle):
    """
    Return transform matrix for rotation around z axis.
    """
    radians = angle * math.pi / 180
    return [
        [math.cos(radians), -math.sin(radians), 0, 0],
        [math.sin(radians), math.cos(radians), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ]

def translate_xyz(x, y, z):
    """
    Return transform matrix for translation (linear moving).
    """
    return [
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1],
    ]

def scale_xyz(x, y, z):
    """
    Return transform matrix for scaling.
    """
    return [
        [x, 0, 0, 0],
        [0, y, 0, 0],
        [0, 0, z, 0],
        [0, 0, 0, 1],
    ]

def matmul(a, b):
    """
    Multiply two matrices. Written in Pure Python
    to avoid dependency on numpy.
    """
    c = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    for x in range(4):
        for y in range(4):
            acc = 0
            for n in range(4):
                acc += a[n][x] * b[y][n]
            c[y][x] = acc
    return c

def multiply_point_by_matrix(matrix, point):
    """
    Multiply a point by a matrix. Written in Pure Python
    to avoid dependency on numpy.
    """
    return [
        (point[0] * matrix[0][0]) + (point[1] * matrix[0][1]) + (point[2] * matrix[0][2]) + (1 * matrix[0][3]),
        (point[0] * matrix[1][0]) + (point[1] * matrix[1][1]) + (point[2] * matrix[1][2]) + (1 * matrix[1][3]),
        (point[0] * matrix[2][0]) + (point[1] * matrix[2][1]) + (point[2] * matrix[2][2]) + (1 * matrix[2][3])
    ]

def point_to_canvas(size, point, z=False):
    """
    Convert to screen coordinates (flip horizontally)
    Only return the first two values [x, y] of point
    """
    if z:
        return [int(size[0] - point[0]), int(point[1]), point[2]]
    else:
        return [int(size[0] - point[0]), int(point[1])]

def draw_line(size, canvas, transform, a, b, color):
    """
    Draw a line on the canvas given two points and transform.
    """
    ta = point_to_canvas(size, multiply_point_by_matrix(transform, a))
    tb = point_to_canvas(size, multiply_point_by_matrix(transform, b))
    canvas.line(ta + tb, fill=color)

def draw_point(size, canvas, transform, point, color):
    """
    Draw a point on the canvas given the transform.
    """
    p = point_to_canvas(size, multiply_point_by_matrix(transform, point))
    canvas.point(p, fill=color)

def draw_point_fake(size, fcanvas, transform, point, color):
    """
    Draw a point on the canvas given the transform.
    """
    p = point_to_canvas(size, multiply_point_by_matrix(transform, point), z=True)
    location = fcanvas[(p[0], p[1])]
    if location is None or location["z"] < p[2]:
        fcanvas[(p[0], p[1])] = {"z": p[2], "color": color}

def render(points_filename, boxes_filename, x, y, z, min_max_x, min_max_y, min_max_z):
    """
    Given to files, points and boxes, a center x, y ,z, and ranges,
    create an image.
    """
    if Image is None:
        raise Exception("Python Image Library is not installed; pip install PIL")
    
    size = (250, 250)
    background_color = (51, 51, 77) # Skybox color

    image = Image.new("RGB", size, background_color)
    canvas = ImageDraw.Draw(image)

    midpoint = [
        (min_max_x[0] + min_max_x[1]) / 2,
        (min_max_y[0] + min_max_y[1]) / 2,
        (min_max_z[0] + min_max_z[1]) / 2,
    ]

    scale = min(
        size[0]/abs(min_max_x[0] - min_max_x[1]),
        size[1]/abs(min_max_y[0] - min_max_y[1]),
    )
    transform = identity()
    # First, center it around zero:
    transform = matmul(transform, translate_xyz(*[-n for n in midpoint]))
    # Now, apply rotations:
    transform = matmul(transform, rotate_z(z))
    transform = matmul(transform, rotate_x(x))
    transform = matmul(transform, rotate_y(y))
    # And then scale
    transform = matmul(transform, scale_xyz(scale, scale, scale))
    # Finally, put it in center of window:
    transform = matmul(transform, translate_xyz(size[0]/2, size[1]/2, 0))

    # Fake canvas:
    fcanvas = defaultdict(lambda: None)

    # Randomize files:
    shuffle(points_filename, filename_out, memory_limit, file_split_count)
    shuffle(boxes_filename, filename_out, memory_limit, file_split_count)
    
    # Draw points first
    with open(points_filename) as fp:
        line = fp.readline()
        while line:
            data = json.loads(line)
            # Each data can be [x, y, z] or [x, y, z, r, g, b]
            # r, g, b is given between 0 and 255 (floats are ok)
            point = data[:3]
            if len(data) > 3:
                color = tuple([int(round(c)) for c in data[3:]])
            else:
                # Default color is white
                color = (255, 255, 255)
            draw_point_fake(size, fcanvas, transform, point, color)
            line = fp.readline()

    # draw fake on canvas
    if fcanvas:
        for x, y in fcanvas:
            color = fcanvas[(x,y)]["color"]
            canvas.point((x,y), fill=color)

    # Draw boxes last to show on top of points
    with open(boxes_filename) as fp:
        line = fp.readline()
        while line:
            data = json.loads(line)
            # Each data is {"segments": [...], "name": "prediction", "color": [r, g, b],
            # "score": Number, "label": "pedestrian"}
            # Each segment is a list of lines,  which is a list of points, which is [x, y, z]
            if "color" in data and data["color"]:
                color = tuple(data["color"])
            else:
                color = (255, 255, 255)  ## default color is white
            for points in data["segments"]:
                point1 = points[0]
                for point2 in points[1:]:
                    draw_line(size, canvas, transform, point1, point2, color)
                    point1 = point2
            line = fp.readline()

    return image

def create_image(points, boxes):
    """
    """
    min_max_x = [float("inf"), float("-inf")]
    min_max_y = [float("inf"), float("-inf")]
    min_max_z = [float("inf"), float("-inf")]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as points_fp:
        for point in points:
            min_max_x = min(point[0], min_max_x[0]), max(point[0], min_max_x[1])
            min_max_y = min(point[1], min_max_y[0]), max(point[1], min_max_y[1])
            min_max_z = min(point[2], min_max_z[0]), max(point[2], min_max_z[1])
            points_fp.write(json.dumps(point))
            points_fp.write("\n")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as boxes_fp:
        for box in boxes:
            for points in box["segments"]:
                for point in points:
                    min_max_x = min(point[0], min_max_x[0]), max(point[0], min_max_x[1])
                    min_max_y = min(point[1], min_max_y[0]), max(point[1], min_max_y[1])
                    min_max_z = min(point[2], min_max_z[0]), max(point[2], min_max_z[1])
            boxes_fp.write(json.dumps(box))
            boxes_fp.write("\n")

    image =  create_thumbnail(
        points_fp.name,
        boxes_fp.name,
        45,
        0,
        45,
        min_max_x,
        min_max_y,
        min_max_z,
    )

    return image
