"""
-*- coding: utf-8 -*- {{{
vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

Copyright (c) 2023, Battelle Memorial Institute
All rights reserved.

1.  Battelle Memorial Institute (hereinafter Battelle) hereby grants
    permission to any person or entity lawfully obtaining a copy of this
    software and associated documentation files (hereinafter "the Software")
    to redistribute and use the Software in source and binary forms, with or
    without modification.  Such person or entity may use, copy, modify, merge,
    publish, distribute, sublicense, and/or sell copies of the Software, and
    may permit others to do so, subject to the following conditions:

    -   Redistributions of source code must retain the above copyright notice,
        this list of conditions and the following disclaimers.

    -	Redistributions in binary form must reproduce the above copyright
        notice, this list of conditions and the following disclaimer in the
        documentation and/or other materials provided with the distribution.

    -	Other than as used herein, neither the name Battelle Memorial Institute
        or Battelle may be used in any form whatsoever without the express
        written consent of Battelle.

2.	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
    ARE DISCLAIMED. IN NO EVENT SHALL BATTELLE OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
    DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
    CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
    LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
    OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
    DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of the FreeBSD Project.

This material was prepared as an account of work sponsored by an agency of the
United States Government. Neither the United States Government nor the United
States Department of Energy, nor Battelle, nor any of their employees, nor any
jurisdiction or organization that has cooperated in the development of these
materials, makes any warranty, express or implied, or assumes any legal
liability or responsibility for the accuracy, completeness, or usefulness or
any information, apparatus, product, software, or process disclosed, or
represents that its use would not infringe privately owned rights.

Reference herein to any specific commercial product, process, or service by
trade name, trademark, manufacturer, or otherwise does not necessarily
constitute or imply its endorsement, recommendation, or favoring by the
United States Government or any agency thereof, or Battelle Memorial Institute.
The views and opinions of authors expressed herein do not necessarily state or
reflect those of the United States Government or any agency thereof.

PACIFIC NORTHWEST NATIONAL LABORATORY
operated by
BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
under Contract DE-AC05-76RL01830
}}}
"""
import operator
from functools import reduce
import math
import re
import os
from collections import defaultdict
from json import loads

## these are all volttron functions only for parsing in json file
_comment_re = re.compile(
    r'((["\'])(?:\\?.)*?\2)|(/\*.*?\*/)|((?:#|//).*?(?=\n|$))',
    re.MULTILINE | re.DOTALL)


def _repl(match):
    """Replace the matched group with an appropriate string."""
    # If the first group matched, a quoted string was matched and should
    # be returned unchanged.  Otherwise a comment was matched and the
    # empty string should be returned.
    return match.group(1) or ''


def strip_comments(string):
    """Return string with all comments stripped.

    Both JavaScript-style comments (//... and /*...*/) and hash (#...)
    comments are removed.
    """
    return _comment_re.sub(_repl, string)


def load_config(config_path):
    """Load a JSON-encoded configuration file."""
    if config_path is None:
        return {}

    if not os.path.exists(config_path):
        print(f"Config file, {config_path} does not exist. load_config returning empty configuration.")
        return {}

    try:
        with open(config_path) as f:
            return parse_json_config(f.read())
    except Exception as e:
        print("Problem parsing agent configuration")
        raise


def parse_json_config(config_str):
    """Parse a JSON-encoded configuration file."""
    return loads(strip_comments(config_str))


##############################################

def extract_criteria(config_matrix):
    """
    Extract pairwise criteria parameters
    :param filename:
    :return:
    """
    if isinstance(config_matrix, str):
        config_matrix = load_config(config_matrix)
    index_of = dict([(a, i) for i, a in enumerate(config_matrix.keys())])

    criteria_labels = []
    for label, index in index_of.items():
        criteria_labels.insert(index, label)

    criteria_matrix = [[0.0 for _ in config_matrix] for _ in config_matrix]
    for j in config_matrix:
        row = index_of[j]
        criteria_matrix[row][row] = 1.0

        for k in config_matrix[j]:
            col = index_of[k]
            criteria_matrix[row][col] = float(config_matrix[j][k])
            criteria_matrix[col][row] = float(1.0 / criteria_matrix[row][col])

    return criteria_labels, criteria_matrix


def calc_column_sums(criteria_matrix):
    """
    Calculate the column sums for the criteria matrix.
    :param criteria_matrix:
    :return:
    """
    j = 0
    cumsum = []
    while j < len(criteria_matrix[0]):
        col = [float(row[j]) for row in criteria_matrix]
        cumsum.append(sum(col))
        j += 1
    return cumsum


def normalize_matrix(criteria_matrix, col_sums):
    """
    Normalizes the members of criteria matrix using the vector
    col_sums. Returns sums of each row of the matrix.
    :param criteria_matrix:
    :param col_sums:
    :return:
    """
    normalized_matrix = []
    row_sums = []
    i = 0
    while i < len(criteria_matrix):
        j = 0
        norm_row = []
        while j < len(criteria_matrix[0]):
            norm_row.append(criteria_matrix[i][j] / (col_sums[j] if col_sums[j] != 0 else 1))
            j += 1
        row_sum = sum(norm_row)
        norm_row.append(row_sum / j)
        row_sums.append(row_sum / j)
        normalized_matrix.append(norm_row)
        i += 1
    return row_sums


def validate_input(pairwise_matrix, col_sums):
    """
    Validates the criteria matrix to ensure that the inputs are

    internally consistent. Returns a True if the matrix is valid,
    and False if it is not.
    :param pairwise_matrix:
    :param col_sums:
    :return:
    """
    # Calculate row products and take the 5th root
    print("Validating matrix")
    random_index = [0, 0, 0, 0.58, 0.9, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]
    roots = []
    for row in pairwise_matrix:
        roots.append(math.pow(reduce(operator.mul, row, 1), 1.0 / 5))
    # Sum the vector of products
    root_sum = sum(roots)
    # Calculate the priority vector
    priority_vec = []
    for item in roots:
        priority_vec.append(item / root_sum)

    # Calculate the priority row
    priority_row = []
    for i in range(0, len(col_sums)):
        priority_row.append(col_sums[i] * priority_vec[i])

    # Sum the priority row
    priority_row_sum = sum(priority_row)

    # Calculate the consistency index
    ncols = max(len(col_sums) - 1, 1)
    consistency_index = \
        (priority_row_sum - len(col_sums)) / ncols

    # Calculate the consistency ratio
    rindex = max(random_index[len(col_sums)], 0.3)
    consistency_ratio = consistency_index / rindex
    print("Inconsistency ratio is: {}".format(consistency_ratio))
    return (consistency_ratio < 0.2), consistency_ratio


def build_score(_matrix, weight, priority):
    """
    Calculates the curtailment score using the normalized matrix
    and the weights vector. Returns a sorted vector of weights for each
    device that is a candidate for curtailment.
    :param _matrix:
    :param weight:
    :param priority:
    :return:
    """
    input_keys, input_values = _matrix.keys(), _matrix.values()
    scores = []

    for input_array in input_values:
        criteria_sum = sum(i * w for i, w in zip(input_array, weight))

        scores.append(criteria_sum * priority)

    return zip(scores, input_keys)


def input_matrix(builder, criteria_labels):
    """
    Construct input normalized input matrix.
    :param builder:
    :param criteria_labels:
    :return:
    """
    sum_mat = defaultdict(float)
    inp_mat = {}
    label_check = builder.values()[-1].keys()
    if set(label_check) != set(criteria_labels):
        raise Exception('Input criteria and data criteria do not match.')
    for device_data in builder.values():
        for k, v in device_data.items():
            sum_mat[k] += v
    for key in builder:
        inp_mat[key] = mat_list = []
        for tag in criteria_labels:
            builder_value = builder[key][tag]
            if builder_value:
                mat_list.append(builder_value / sum_mat[tag])
            else:
                mat_list.append(0.0)

    return inp_mat


if __name__ == "__main__":

    criteria_labels, criteria_array = extract_criteria({
        "zonetemperature_setpoint": {
            "room_type": 0.5,
            "available_zone_airflow_ratio": 2.0,
            "box_size": 1.0
        },
        "room_type": {
            "available_zone_airflow_ratio": 4.0,
            "box_size": 2.0
        },
        "available_zone_airflow_ratio": {
            "box_size": 2.0
        },
        "box_size": {}
    })
    col_sums = calc_column_sums(criteria_array)
    row_average = normalize_matrix(criteria_array, col_sums)
    print("VALIDATE - criteria_array {} - col_sums {}".format(criteria_array, col_sums))
    result, ratio = validate_input(criteria_array, col_sums)
    if result:
        print("Validation passed.")
    else:
        print(f"Validation failed. Inconsistency ratio is {ratio}")
