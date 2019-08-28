from __future__ import absolute_import
from aiida_spex.tools.structure import cartesian_to_internal, inverse
import numpy as np 

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
    ]
)

print("Initial Positions:")
cartesian_to_internal(cartesian_coordinates, inverse(bravais_matrix))
