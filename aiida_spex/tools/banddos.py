#!/usr/bin/python3

import numpy as np
import h5py
import csv
import os
import argparse
import os.path

def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return open(arg, 'r')  # return an open file handle

parser = argparse.ArgumentParser(
    description='process info which is not available in the metadata')
parser.add_argument("--fermi", type=float,
                    help="provide fermi energy corresponding to the k-path", required=False)

args = parser.parse_args()

hdffilename='/Users/chand/workbench/work/materials_docs/data/fleur/banddos_jc2.hdf'

eV = 27.211386
f = h5py.File(hdffilename, 'r')
_atomicNum = f.get('atoms/atomicNumbers')
atomicNum = np.array(_atomicNum)
_atomicPos = f.get('atoms/positions')
atomicPos = np.array(_atomicPos)
_atomicGroup = f.get('atoms/equivAtomsGroup')
atomicGroup = np.array(_atomicGroup)
_reciprocalCell = f.get('cell/reciprocalCell')
reciprocalCell = np.array(_reciprocalCell)
fermiEnergy = f.get('general').attrs.get('lastFermiEnergy')[0]

# 'eigenvalues', 'jsym', 'ksym', 'lLikeCharge', 'numFoundEigenvals'
_eig = f.get('eigenvalues')
_lcharge = _eig.get('lLikeCharge')

# lcharge (jspin, kpts, band-index, atom-index, lcharge)
# "lLikeCharge": shape (1, 215, 61, 12, 4)
lcharge = np.array(_lcharge)
# np.sum(lcharge[0][0][0][3][:])

_kpts = f.get('kpts')
_kpts.keys()
_kcoord = _kpts.get('coordinates')
kcoord = np.array(_kcoord)
_hsymmI = _kpts.get('specialPointIndices')
hsymmI = np.array(_hsymmI)

_eigVal = f.get('eigenvalues/eigenvalues')
eigVal = np.array(_eigVal)
# eigVal.shape

fermiEnergy = -0.204
# fermiEnergy =  args.fermi 
print("K-mesh Fermi energy = ", fermiEnergy)


# Claculating the K-point path
def kpath(kcoord):
    '''find kpath from an array of [kx,ky,kz] vector

    k-path for the band plot

    Arguments:
        kcoord {list} -- list of vectors

    Returns:
        kpts -- array of k points
    '''
    nkpt = kcoord.shape[0]
    kpts = np.zeros(nkpt)
    kpts[0] = np.linalg.norm(reciprocalCell.dot(kcoord[0]))
    for i in range(1, nkpt):
        kpts[i] = kpts[i - 1] + \
            np.linalg.norm(reciprocalCell.dot(
                kcoord[i]) - reciprocalCell.dot(kcoord[i - 1]))
    return kpts

# print(kpath(kcoord))

def writeBand(fileName, kpts, eigVal):
    '''writes atom-type contribution to bandstructure

    writes out the band index, kpt, energy, atom contributions

    Arguments:
        fileName {strin} -- out file name
        kpts {array} -- k-points x-axis in band plot
        eigVal {array} -- y-axis in band plot
    '''
    jspin, nkpt, nbnd, jatom, lc = lcharge.shape
    with open(fileName, 'w') as csvFile:
        bandWriter = csv.writer(csvFile, delimiter=',',
                                quotechar="|", quoting=csv.QUOTE_MINIMAL)
        bandWriter.writerow(['jband', 'k', 'e', ','.join(
            map(str, ['Z{}'.format(i) for i in atomicGroup]))])
        for h in range(jspin):
            for i in range(nbnd - 1):
                for j in range(nkpt - 1):

                    bandWriter.writerow(
                        [i,
                         '{:.3f}'.format(kpts[j]), '{:.3f}'.format(
                             eV * (eigVal[h, j, i] - fermiEnergy)),
                         ','.join(map(str, ['{:.3f}'.format(
                             np.sum(lcharge[h, j, i, k, :])) for k in range(jatom)]))
                         ])
    os.system("sed -i '' 's/|//g' " + fileName)

# for s,p,d,f


def writelCharge(fileName, kpts, lcharge):
    '''writes s,p,d,f orbital contributions of each atom

    writes out the band index, kpt, energy, atom contribution, atom-orbital contribution

    Arguments:
        fileName {strin} -- name of the out file
        kpts {array} -- parsed from banddos
        lcharge {array} -- parsed from banddos
    '''
    jspin, nkpt, nbnd, jatom, lc = lcharge.shape
    with open(fileName, 'w') as csvFile:
        bandWriter = csv.writer(csvFile, delimiter=',',
                                quotechar="|", quoting=csv.QUOTE_MINIMAL)
        bandWriter.writerow(['jband', 'k', 'e', ','.join(map(str, ['Z{}'.format(i) for i in atomicGroup])),
                             ','.join(map(str, [','.join(map(
                                 str, ['Z' + str(k) + '_{}'.format(j) for j in range(lc)])) for k in atomicGroup]))
                             ])
        for h in range(jspin):
            for i in range(nbnd - 1):
                for j in range(nkpt - 1):
                    for k in range(jatom - 1):
                        bandWriter.writerow(
                            [i,
                             '{:.3f}'.format(kpts[j]),
                             '{:.3f}'.format(
                                 eV * (eigVal[h, j, i] - fermiEnergy)),
                             ','.join(map(str, ['{:.3f}'.format(
                                 np.sum(lcharge[h, j, i, k, :])) for k in range(jatom)])),
                             ','.join(map(str, [','.join(map(str, ['{:.3f}'.format(
                                 lcharge[h, j, i, k, l]) for l in range(lc)])) for k in range(jatom)]))
                             ])
    os.system("sed -i '' 's/|//g' " + fileName)


def writeDos(infile, outfile):
    '''Parse and write dos file from fleur

    DOS.x files are pared in this function. same order of columns are maintained...
    ...but comma separatd and with column heading

    Arguments:
        infile {string} -- input file name 
        outfile {string} -- output file lname 
    '''
    # e, totalDOS, interstitial, vac1, vac2, atomDOs*, lDOS*
    dos = np.loadtxt(infile)
    row, colum = dos.shape
    jspin, nkpt, nbnd, jatom, lc = lcharge.shape
    with open(outfile, 'w') as csvFile:
        dosWriter = csv.writer(csvFile, delimiter=',',
                               quotechar="|", quoting=csv.QUOTE_MINIMAL)
        dosWriter.writerow(['e', 'tDOS', 'inter', 'vac1', 'vac2', ','.join(map(str, ['Z{}'.format(i) for i in atomicGroup])), ','.join(
            map(str, [','.join(map(str, ['Z' + str(k) + '_{}'.format(j) for j in range(lc)])) for k in atomicGroup]))])
        for i in range(row):
            dosWriter.writerow(['{:.3f}'.format(dos[i, j])
                                for j in range(colum)])
    os.system("sed -i '' 's/|//g' " + outfile)

writeBand('banddos_jc.csv', kpath(kcoord), eigVal)
# writelCharge('lband.csv', kpath(kcoord), lcharge)
# writeDos('data/fleur/DOS.1', 'dos.csv')
