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

"""
extracts band data from spex_???.out files
"""
import numpy as np
import csv
import re
import argparse

parser = argparse.ArgumentParser(
    description="process info which is not available in the metadata"
)
parser.add_argument(
    "--fermiKS",
    type=float,
    help="provide fermi energy corresponding to the k-path",
    required=False,
)
parser.add_argument(
    "--fermiGW",
    type=float,
    help="provide fermi energy corresponding to the k-path",
    required=False,
)

args = parser.parse_args()


def reciprocalLattice(lat):
    """create reciprocal lattice from a real one
    Arguments:
        lat {array} -- (3X3 numpy) list of  realspace lattice vectors
    Returns:
        [array] -- (3X3 numpy) list of reciprocal lattice vectors
    """
    unitCellVolume = lat[0].dot(np.cross(lat[1], lat[2]))
    b0 = 2 * np.pi * np.cross(lat[1], lat[2]) / unitCellVolume
    b1 = 2 * np.pi * np.cross(lat[2], lat[0]) / unitCellVolume
    b2 = 2 * np.pi * np.cross(lat[0], lat[1]) / unitCellVolume
    rlat = np.array([b0, b1, b2])
    return rlat


def getInfo(spexOutFileName, qptsFilename):
    """Information regarding the system under consideration

    Arguments:
        spexOutFileName {sring} -- spex out file name (for sampling)
        qptsFilename {string} -- qpts file name

    Returns:
        lat -- real space lattice vectors
        rlat -- reciprocal space lattice vectors
        nqpts -- number of qpts (points in the kpath)
        kcoord -- k-path coordinates
    """
    START_PATTERN = "Lattice parameter"
    END_PATTERN = "Unit-cell volume"
    lat = []
    with open(spexOutFileName, "rt") as file:
        match = False
        for line in file:
            if re.search(START_PATTERN, line):
                match = True
                continue
            elif re.search(END_PATTERN, line):
                match = False
                continue
            elif match:
                lat.append(
                    (re.sub("[A-Za-z=]*", "", line)).strip(" ").rstrip("\n").split()
                )

    lat = np.array(lat).astype(float)
    rlat = reciprocalLattice(lat)
    qpts = []
    with open(qptsFilename, "rt") as _qpts:
        for line in _qpts:
            qpts.append(line.rstrip("\n").strip(" "))

    qpts = np.array(qpts)
    nqpts = int(qpts[0].split()[0])
    scaleqpts = float(qpts[0].split()[1])

    # create k-path from k-coordinates
    kcoord = []
    for i in range(1, nqpts + 1):
        kcoord.append([float(j) / scaleqpts for j in qpts[i].split()[0:3]])
    kcoord = np.array(kcoord)

    return lat, rlat, nqpts, kcoord


def kpath(kcoord, reciprocalCell):
    """construnct k-path from k coordinates
    Arguments:
        kcoord {list} -- array of [kx,ky,kz]
    Returns:
        [list] -- kpath
    """
    nkpt = kcoord.shape[0]
    kpts = np.zeros(nkpt)
    kpts[0] = np.linalg.norm(reciprocalCell.dot(kcoord[0]))
    for i in range(1, nkpt):
        kpts[i] = kpts[i - 1] + np.linalg.norm(
            reciprocalCell.dot(kcoord[i]) - reciprocalCell.dot(kcoord[i - 1])
        )

    return kpts


def spexBand(nqpts):
    """Collect band informations from the spex_???.out files"""
    spexReBand = []
    spexImBand = []
    START_PATTERN = "Bd"
    END_PATTERN = "Timing \(quasiparticle equation\)"

    for i in range(1, nqpts + 1):
        spexOutName = "spex_" + "{0:03}".format(i) + ".out"
        fileName = "data/spex/" + spexOutName
        # print(fileName)
        _diag = []
        with open(fileName, "rt") as file:
            match = False
            for line in file:
                if re.search(START_PATTERN, line):
                    match = True
                    continue
                elif re.search(END_PATTERN, line):
                    match = False
                    continue
                elif match:
                    _diag.append(line.rstrip("\n"))

        _diag = np.array(_diag)
        # twice the number of bands + includes an empty...
        nbands2 = len(_diag) - 1
        # ...line line at the end(hence the -1 to remove it)

        reDiag = []
        imDiag = []
        for i in range(0, nbands2):
            if i % 2 == 0:
                reDiag.append([float(j) for j in _diag[i].split()])
            if i % 2 != 0:
                imDiag.append([float(j) for j in _diag[i].split()])

        reDiag = np.array(reDiag)
        spexReBand.append(reDiag)
        spexImBand.append(imDiag)

    spexReBand = np.array(spexReBand)
    spexImBand = np.array(spexImBand)

    return spexReBand, spexImBand


def writeBand(
    fileName,
    kpts,
    spexReBand,
    spexImBand,
):
    """Write to a csv file
    Arguments:
        fileName {string} -- name of the output file
        kpts {list} -- k-path
    """
    iband = int(spexReBand[0][0][0])  # initial band
    fband = int(spexReBand[0][-1][0])  # final band
    nkpt = len(kpts)
    with open(fileName, "w") as csvFile:
        bandWriter = csv.writer(
            csvFile, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        bandWriter.writerow(["jband", "k", "eKS", "eGW", "imGW"])
        irun = 0
        for i in range(iband, fband + 1):
            for ikpt in range(nkpt - 1):
                bandWriter.writerow(
                    [
                        i,
                        "{:.3f}".format(kpts[ikpt]),
                        "{:.3f}".format(spexReBand[ikpt][irun][5] - fermiKS),
                        "{:.3f}".format(spexReBand[ikpt][irun][7] - fermiGW),
                        "{:.3f}".format(spexImBand[ikpt][irun][-2]),
                    ]
                )
            irun += 1


# EXTRACT

fermiKS = 2.04996
fermiGW = 2.274363447
# fermiKS = args.fermiKS
# fermiGW = args.fermiGW
lat, rlat, nqpts, kcoord = getInfo("data/spex/spex_001.out", "data/spex/qpts")
kpts = kpath(kcoord, rlat)
spexReBand, spexImBand = spexBand(nqpts)
writeBand("spexband.csv", kpts, spexReBand, spexImBand)
