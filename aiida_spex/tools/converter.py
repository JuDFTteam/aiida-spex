# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-SPEX package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-spex     #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
###############################################################################

from __future__ import absolute_import
import numpy as np


def inverse(bravais_matrix):
    return np.linalg.inv(bravais_matrix)


def cartesian_to_internal(coordinate_vectors, bravais_matrix):
    result = []
    for coordinate_vector in coordinate_vectors:
        result.append(np.inner(bravais_matrix, coordinate_vector))
    return result


def internal_to_cartesian(coordinate_vectors, bravais_matrix):
    result = []
    for coordinate_vector in coordinate_vectors:
        result.append(np.dot(coordinate_vector, bravais_matrix))
    return result


if __name__ == "__main__":

    # test functions
    #
    bravais_matrix = np.array(
        [[9.2974, 9.2974, 0.00], [-16.103569, 16.103569, 0.0], [0.0, 0.0, 13.5100]]
    )

    cartesian_coordinates = np.array(
        [
            [9.2974000000, 0.0000000000, 1.0650000000],
            [0.0000000000, -2.6838208393, -3.0650000000],
            [2.3243500000, 1.3420714553, -3.0650000000],
            [4.6487000000, 5.3679637499, -3.0650000000],
            [-2.3243500000, -6.7097131338, -3.0650000000],
            [4.6487000000, -2.6838208393, -3.0650000000],
            [6.9730500000, 1.3420714553, -3.0650000000],
            [0.0000000000, -10.7356054284, -3.0650000000],
            [-2.3243500000, 9.3938560445, -3.0650000000],
            [0.0000000000, 13.4197483390, -3.0650000000],
            [0.0000000000, 5.3679637499, -3.0650000000],
        ]
    )

    cartesian_coordinates2 = np.array(
        [
            [9.2974000000, 0.0000000000, 1.0712857790],
            [0.0000000000, -2.6862280017, -3.0650000000],
            [2.3182773004, 1.3453978146, -3.0650000000],
            [4.6426894952, 5.3713997023, -3.0650000000],
            [-2.3223581421, -6.7086719805, -3.0650000000],
            [4.6286496329, -2.6955052899, -3.0650000000],
            [6.9571045896, 1.3511712332, -3.0845330662],
            [0.0000000000, -10.7125621473, -3.0650000000],
            [-2.3244123512, 9.3867738629, -3.0650000000],
            [0.0000000000, 13.4012299752, -3.0845417143],
            [0.0000000000, 5.3678571960, -3.0650000000],
        ]
    )

    print("Initial Positions:")
    cartesian_to_internal(cartesian_coordinates, inverse(bravais_matrix))

    print("Relaxed Positions:")
    cartesian_to_internal(cartesian_coordinates2, inverse(bravais_matrix))
    import subprocess

    subprocess.run(["which", "python"])
