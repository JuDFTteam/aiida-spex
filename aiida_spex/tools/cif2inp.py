#!/usr/bin/python3
import sys
import pymatgen as mg
cifFilename=sys.argv[1]
structure=mg.Structure.from_file(cifFilename)

structureFormula=structure.formula.replace(" ", "")
inpFilename='inp_'+structureFormula

with open(inpFilename,"w+") as f:
    natoms=len(structure.atomic_numbers)
    f.write(structureFormula+"\r\n")
    f.write("&input film=F /\r\n")
    for i in range(3):
        f.write(' '.join(map("{:.4f}".format,structure.lattice.matrix[i]))+"\r\n")
    f.write("1.8897 \r\n1.0000 1.0000 1.0000 \r\n\r\n")
    f.write(str(natoms)+"\r\n")
    for i in range(natoms):
        f.write(str(structure.atomic_numbers[i])+" "
                +" ".join(map("{:.4f}".format, structure.frac_coords[i]))+"\r\n")
    f.write("\r\n")
        
