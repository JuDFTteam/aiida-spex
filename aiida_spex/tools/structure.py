import numpy as np


def inverse(bravais_matrix):
    return np.linalg.inv(bravais_matrix)


def cartesian_to_internal(coordinate_vectors, bravais_matrix):
    for coordinate_vector in coordinate_vectors:
        print(np.inner(bravais_matrix, coordinate_vector))


if __name__ == "__main__":

    # test functions
    #
    bravais_matrix = np.array(
        [[9.2974, 9.2974, 0.00], [-16.103569, 16.103569, 0.0], [0.0, 0.0, 13.5100]]
    )

    inverse_bravais_matrix = inverse(bravais_matrix)
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
    cartesian_to_internal(cartesian_coordinates, inverse_bravais_matrix)

    print("Relaxed Positions:")
    cartesian_to_internal(cartesian_coordinates2, inverse_bravais_matrix)
