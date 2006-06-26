"""
cclib is a parser for computational chemistry log files.

See http://cclib.sf.net for more information.

Copyright (C) 2006 Noel O'Boyle and Adam Tenderholt

 This program is free software; you can redistribute and/or modify it
 under the terms of the GNU General Public License as published by the
 Free Software Foundation; either version 2, or (at your option) any later
 version.

 This program is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY, without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 General Public License for more details.

Contributions (monetary as well as code :-) are encouraged.
"""
import Numeric
import random # For sometimes running the progress updater
import utils
import logfileparser

class ADF(logfileparser.Logfile):
    """An ADF log file"""
    SCFCNV, SCFCNV2 = range(2) #used to index self.scftargets[]
    maxelem, norm = range(2) # used to index scf.values
    def __init__(self, *args):

        # Call the __init__ method of the superclass
        super(ADF, self).__init__(logname="ADF", *args)
        
    def __str__(self):
        """Return a string representation of the object."""
        return "ADF log file %s" % (self.filename)

    def __repr__(self):
        """Return a representation of the object."""
        return 'ADF("%s")' % (self.filename)

    def normalisesym(self, label):
        """Use standard symmetry labels instead of ADF labels.

        To normalise:
        (1) any periods are removed (except in the case of greek letters)
        (2) XXX is replaced by X, and a " added.
        (3) XX is replaced by X, and a ' added.
        (4) The greek letters Sigma, Pi, Delta and Phi are replaced by
            their lowercase equivalent.

        >>> sym = ADF("dummyfile").normalisesym
        >>> labels = ['A','s','A1','A1.g','Sigma','Pi','Delta','Phi','Sigma.g','A.g','AA','AAA','EE1','EEE1']
        >>> map(sym,labels)
        ['A', 's', 'A1', 'A1g', 'sigma', 'pi', 'delta', 'phi', 'sigma.g', 'Ag', "A'", 'A"', "E1'", 'E1"']
        """
        greeks = ['Sigma', 'Pi', 'Delta', 'Phi']
        for greek in greeks:
            if label.startswith(greek):
                return label.lower()
            
        ans = label.replace(".", "")
        l = len(ans)
        if l > 1 and ans[0] == ans[1]: # Python only tests the second condition if the first is true
            if l > 2 and ans[1] == ans[2]:
                ans = ans.replace(ans[0]*3, ans[0]) + '"'
            else:
                ans = ans.replace(ans[0]*2, ans[0]) + "'"
        return ans
        

    def parse(self, fupdate=0.05, cupdate=0.002):
        """Extract information from the logfile."""
        inputfile = open(self.filename, "r")
        
        if self.progress:
            
            inputfile.seek(0, 2) #go to end of file
            nstep = inputfile.tell()
            inputfile.seek(0)
            self.progress.initialize(nstep)
            oldstep = 0
            
        # Used to avoid extracting the final geometry twice in a GeoOpt
        NOTFOUND, GETLAST, NOMORE = range(3)
        finalgeometry = NOTFOUND 
        
        # Used for calculating the scftarget (variables names taken from the ADF manual)
        accint = SCFconv = sconv2 = None
        
        # keep track of nosym and unrestricted case to parse Energies since it doens't have an all Irreps section
        nosymflag = False
        unrestrictedflag = False
        
        for line in inputfile:
            
            if self.progress and random.random() < cupdate:
                step = inputfile.tell()
                if step != oldstep:
                    self.progress.update(step, "Unsupported Information")
                    oldstep = step
                
            if line.find("INPUT FILE") >= 0:
#check to make sure we aren't parsing Create jobs
                while line:
                
                    if self.progress and random.random() < fupdate:
                        step = inputfile.tell()
                        #if step!=oldstep:
                        self.progress.update(step, "Unsupported Information")
                        oldstep = step
                  
                    if line.find("INPUT FILE") >= 0:
                        line2 = inputfile.next()
                    if line2.find("Create") < 0:
                        break
                            
                    line = inputfile.next()
            
            if line[1:10] == "Symmetry:":
                info = line.split()
                if info[1] == "NOSYM":
                    nosymflag = True

            if line[4:13] == 'Molecule:':
                info = line.split()
                if info[1] == 'UNrestricted':
                    unrestrictedflag = True

            if line[1:6] == "ATOMS":
# Find the number of atoms and their atomic numbers
# Also extract the starting coordinates (for a GeoOpt anyway)
                if self.progress and random.random() < cupdate:
                    step = inputfile.tell()
                    if step != oldstep:
                        self.progress.update(step, "Attributes")
                        oldstep = step
                
                self.logger.info("Creating attribute atomnos[], atomcoords[]")
                self.atomnos = []
                self.atomcoords = []
                
                underline = inputfile.next()  #clear pointless lines
                label1 = inputfile.next()     # 
                label2 = inputfile.next()     #
                line = inputfile.next()
                atomcoords = []
                while len(line)>2: #ensure that we are reading no blank lines
                    info = line.split()
                    element = info[1].split('.')[0]
                    self.atomnos.append(self.table.number[element])
                    atomcoords.append(map(float, info[2:5]))
                    line = inputfile.next()
                self.atomcoords.append(atomcoords)
                
                self.natom = len(self.atomnos)
                self.logger.info("Creating attribute natom: %d" % self.natom)
                
            if line[1:22] == "S C F   U P D A T E S":
# find targets for SCF convergence

                if not hasattr(self,"scftargets"):
                    self.logger.info("Creating attribute scftargets[]")
                    self.scftargets = []

                #underline, blank, nr
                for i in range(3):
                    inputfile.next()

                line = inputfile.next()
                SCFconv = float(line.split()[-1])
                line = inputfile.next()
                sconv2 = float(line.split()[-1])
              
            if line[1:11] == "CYCLE    1":
              
                if self.progress and random.random() < fupdate:
                    step = inputfile.tell()
                    if step != oldstep:
                        self.progress.update(step, "QM Convergence")
                        oldstep = step
              
                newlist = []
                line = inputfile.next()

                if not hasattr(self,"geovalues"):
                    # This is the first SCF cycle
                    self.scftargets.append([sconv2*10, sconv2])
                elif finalgeometry in [GETLAST, NOMORE]:
                    # This is the final SCF cycle
                    self.scftargets.append([SCFconv*10, SCFconv])
                else:
                    # This is an intermediate SCF cycle
                    oldscftst = self.scftargets[-1][1]
                    grdmax = self.geovalues[-1][1]
                    scftst = max(SCFconv, min(oldscftst, grdmax/30, 10**(-accint)))
                    self.scftargets.append([scftst*10, scftst])
                        
                while line.find("SCF CONVERGED") == -1:
                    if line[4:12] == "SCF test":
                        if not hasattr(self, "scfvalues"):
                            self.logger.info("Creating attribute scfvalues")
                            self.scfvalues = []
                                                
                        info = line.split()
                        newlist.append([float(info[4]), abs(float(info[6]))])
                    try:
                        line = inputfile.next()
                    except StopIteration: #EOF reached?
                        break            

                if hasattr(self, "scfvalues"):
                    self.scfvalues.append(newlist)
              
            if line[51:65] == "Final Geometry":
                finalgeometry = GETLAST
            
            if line[1:24] == "Coordinates (Cartesian)" and finalgeometry in [NOTFOUND, GETLAST]:
                # Get the coordinates from each step of the GeoOpt
                if not hasattr(self, "atomcoords"):
                    self.logger.info("Creating attribute atomcoords")
                    self.atomcoords = []
                equals = inputfile.next()
                blank = inputfile.next()
                title = inputfile.next()
                title = inputfile.next()
                hyphens = inputfile.next()

                atomcoords = []
                line = inputfile.next()
                while line != hyphens:
                    atomcoords.append(map(float, line.split()[5:8]))
                    line = inputfile.next()
                self.atomcoords.append(atomcoords)
                if finalgeometry == GETLAST: # Don't get any more coordinates
                    finalgeometry = NOMORE

            if line[1:27] == 'Geometry Convergence Tests':
# Extract Geometry convergence information
                if not hasattr(self, "geotargets"):
                    self.logger.info("Creating attributes geotargets[], geovalues[[]]")
                    self.geovalues = []
                    self.geotargets = Numeric.array([0.0, 0.0, 0.0, 0.0, 0.0], "f")
                if not hasattr(self, "scfenergies"):
                    self.logger.info("Creating attribute scfenergies[]")
                    self.scfenergies = []
                equals = inputfile.next()
                blank = inputfile.next()
                line = inputfile.next()
                temp = inputfile.next().strip().split()
                self.scfenergies.append(utils.convertor(float(temp[-1]), "hartree", "eV"))
                for i in range(6):
                    line = inputfile.next()
                values = []
                for i in range(5):
                    temp = inputfile.next().split()
                    self.geotargets[i] = float(temp[-3])
                    values.append(float(temp[-4]))
                self.geovalues.append(values)
 
            if line[1:27] == 'General Accuracy Parameter':
                # Need to know the accuracy of the integration grid to
                # calculate the scftarget...note that it changes with time
                accint = float(line.split()[-1])
            
            if line[1:37] == 'Orbital Energies, per Irrep and Spin' and not hasattr(self, "mosyms") and nosymflag and not unrestrictedflag:
#Extracting orbital symmetries and energies, homos for nosym case
#Should only be for restricted case because there is a better text block for unrestricted and nosym
                
                underline = inputfile.next()
                header = inputfile.next()
                underline = inputfile.next()
                label = inputfile.next()
                line = inputfile.next()

                info = line.split()
                if not info[0] == '1':
                    self.logger.error("MO info up to #%s is missing" % info[0])
                
                else:
                    self.logger.info("Creating attribute mosyms[[]]")
                    self.mosyms = [[]]

                    self.logger.info("Creating attribute moenergies[[]]")
                    self.moenergies = [[]]
                
                    homoA = None

                    while len(line) > 3:
                        info = line.split()
                        self.mosyms[0].append('A')
                        self.moenergies[0].append(utils.convertor(float(info[2]), 'hartree', 'eV'))
                        if info[1] == '0.000' and not hasattr(self, 'homos'):
                            self.logger.info("Creating attribute homos[]")
                            self.homos = [len(self.moenergies[0]) - 2]
                        line = inputfile.next()

                    temp = Numeric.array(self.moenergies, "f")
                    self.moenergies = temp
                    self.homos = Numeric.array(self.homos, "i")

            if line[1:29] == 'Orbital Energies, both Spins' and not hasattr(self, "mosyms") and nosymflag and unrestrictedflag:
#Extracting orbital symmetries and energies, homos for nosym case
#should only be here if unrestricted and nosym

                self.logger.info("Creating attribute mosymms[[]]")
                self.mosyms = [[], []]

                self.logger.info("Creating attribute moenergies[[]]")
                self.moenergies = [[], []]

                underline = inputfile.next()
                blank = inputfile.next()
                header = inputfile.next()
                underline = inputfile.next()
                line = inputfile.next()

                homoa = None
                homob = None

                while len(line) > 5:
                    info = line.split()
                    if info[2] == 'A': 
                        self.mosyms[0].append('A')
                        self.moenergies[0].append(utils.convertor(float(info[4]), 'hartree', 'eV'))
                        if info[3] == '0.00' and not homoa:
                            homoa = len(self.moenergies[0]) - 2
                    elif info[2] == 'B':
                        self.mosyms[1].append('A')
                        self.moenergies[1].append(utils.convertor(float(info[4]), 'hartree', 'eV'))
                        if info[3] == '0.00' and not homob:
                            homob = len(self.moenergies[0]) - 2
                    else:
                        print "Error reading line: %s" % line

                    line = inputfile.next()

                temp = Numeric.array(self.moenergies, "f")
                self.moenergies = temp
                self.logger.info("Creating attribute homos[]")
                self.homos = Numeric.array([homoa, homob], "i")


            if line[1:29] == 'Orbital Energies, all Irreps' and not hasattr(self, "mosyms"):
#Extracting orbital symmetries and energies, homos
                self.logger.info("Creating attribute mosyms[[]]")
                self.mosyms = [[]]
                
                self.logger.info("Creating attribute moenergies[[]]")
                self.moenergies = [[]]
                
                underline = inputfile.next()
                blank = inputfile.next()
                header = inputfile.next()
                underline2 = inputfile.next()
                line = inputfile.next()
                
                homoa = None
                homob = None
  
                while len(line) == 77:
                    info = line.split()
                    if len(info) == 5: #this is restricted
                        self.mosyms[0].append(self.normalisesym(info[0]))
                        self.moenergies[0].append(utils.convertor(float(info[3]), 'hartree', 'eV'))
                        if info[2] == '0.00' and not hasattr(self, 'homos'):
                            self.logger.info("Creating attribute homos[]")
                            self.homos = [len(self.moenergies[0]) - 2]
                        line = inputfile.next()
                    elif len(info) == 6: #this is unrestricted
                        if len(self.moenergies) < 2: #if we don't have space, create it
                            self.moenergies.append([])
                            self.mosyms.append([])
                        if info[2] == 'A':
                            self.mosyms[0].append(self.normalisesym(info[0]))
                            self.moenergies[0].append(utils.convertor(float(info[4]), 'hartree', 'eV'))
                            if info[3] == '0.00' and homoa == None:
                                homoa = len(self.moenergies[0]) - 2
                                
                        if info[2] == 'B':
                            self.mosyms[1].append(self.normalisesym(info[0]))
                            self.moenergies[1].append(utils.convertor(float(info[4]), 'hartree', 'eV'))
                            if info[3] == '0.00' and homob == None:
                                homob = len(self.moenergies[1]) - 2
                                
                        line = inputfile.next()
                        
                    else: #different number of lines
                        print "Error", info
      
                if len(info) == 6: #still unrestricted, despite being out of loop
                    self.logger.info("Creating attribute homos[]")
                    self.homos = [homoa, homob]
    
#                tempa=Numeric.array(self.moenergies[0],"f")
#                tempb=Numeric.array(self.moenergies[1],"f")
#                self.moenergies=[tempa,tempb]
#              elif len(info)==5:
#                self.moenergies=[

                temp = Numeric.array(self.moenergies, "f")
                self.moenergies = temp
                self.homos = Numeric.array(self.homos, "i")
  
            if line[1:24] == "List of All Frequencies":
# Start of the IR/Raman frequency section
                if self.progress and random.random() < fupdate:
                    step = inputfile.tell()
                    if step != oldstep:
                        self.progress.update(step, "Frequency Information")
                        oldstep = step
                         
#                 self.vibsyms = [] # Need to look into this a bit more
                self.vibirs = []
                self.vibfreqs = []
#                 self.logger.info("Creating attribute vibsyms[]")
                self.logger.info("Creating attribute vibfreqs[], vibirs[]")
                for i in range(8):
                    line = inputfile.next()
                line = inputfile.next().strip()
                while line:
                    temp = line.split()
                    self.vibfreqs.append(float(temp[0]))                    
                    self.vibirs.append(float(temp[2])) # or is it temp[1]?
                    line = inputfile.next().strip()
                self.vibfreqs = Numeric.array(self.vibfreqs, "f")
                self.vibirs = Numeric.array(self.vibirs, "f")
                if hasattr(self, "vibramans"):
                    self.vibramans = Numeric.array(self.vibramans, "f")


#******************************************************************************************************************8
#delete this after new implementation using smat, eigvec print,eprint?
            if line[1:49] == "Total nr. of (C)SFOs (summation over all irreps)":
# Extract the number of basis sets
                self.nbasis = int(line.split(":")[1].split()[0])
                self.logger.info("Creating attribute nbasis: %i" % self.nbasis)
                   
   # now that we're here, let's extract aonames
   
                self.logger.info("Creating attribute fonames[]")
                self.fonames = []
                   
                blank = inputfile.next()
                note = inputfile.next()
                symoffset = 0
                blank = inputfile.next(); blank = inputfile.next(); blank = inputfile.next()
                
                nosymreps = []
                while len(self.fonames) < self.nbasis:
                            
                    sym = inputfile.next()
                    line = inputfile.next()
                    num = int(line.split(':')[1].split()[0])
                    nosymreps.append(num)
                       
                    #read until line "--------..." is found
                    while line.find('-----') < 0:
                        line = inputfile.next()
                       
                    #for i in range(num):
                    while len(self.fonames) < symoffset + num:
                        line = inputfile.next()
                        info = line.split()
                          
                        #index0 index1 occ2 energy3/4 fragname5 coeff6 orbnum7 orbname8 fragname9
                        orbname = info[8]
                        orbital = info[7] + orbname.replace(":", "")
                          
                        fragname = info[5]
                        frag = fragname + info[9]
                          
                        coeff = float(info[6])
                        sum = coeff**2
                        while sum < 1.0:
                        #if coeff**2 <= 1.0: #is this a linear combination?
                            
                            line = inputfile.next()
                            info = line.split()
                              
                            if line[42] == ' ' and len(info) > 4: #no new fragment/atom type and energy on line
                                frag += "+" + fragname + info[6]
                                coeff = float(info[3])
                                if coeff < 0:
                                    orbital += '-' + info[4] + info[5].replace(":", "")
                                else:
                                    orbital += '+' + info[4] + info[5].replace(":", "")

                            elif line[42] == ' ': #no new fragment/atom type, but no energy on line
                                frag += "+" + fragname + info[3]
                                coeff = float(info[0])
                                if coeff < 0:
                                    orbital += '-' + info[1] + info[2].replace(":","")
                                else:
                                    orbital += '+' + info[1] + info[2].replace(":","")

                            else:
                                frag += "+" + info[3] + info[7]
                                coeff = float(info[4])
                                if coeff < 0:
                                    orbital += '-' + info[5] + info[6].replace(":", "")
                                else:
                                    orbital += "+" + info[5] + info[6].replace(":", "")
                            
                            sum += coeff**2
                            
                        if sum == coeff**2: #if we did not go into the while loop, read a new line
                            inputfile.next()

                        self.fonames.append("%s_%s" % (frag, orbital))
                    symoffset += num
                    
                    #nextline blankline blankline
                    inputfile.next(); inputfile.next(); inputfile.next()
                    
                    
            if line[1:32] == "S F O   P O P U L A T I O N S ,":
#Extract overlap matrix

                self.logger.info("Creating attribute fooverlaps[x, y]")
                self.fooverlaps = Numeric.zeros((self.nbasis, self.nbasis), "float")
                
                symoffset = 0
                
                for nosymrep in nosymreps:
                            
                    line = inputfile.next()
                    while line.find('===') < 10: #look for the symmetry labels
                        line = inputfile.next()
                    #blank blank text blank col row
                    for i in range(6):
                        inputfile.next()
                    
                    base = 0
                    
                    while base < nosymrep: #have we read all the columns?
                          
                        for i in range(nosymrep - base):
                        
                            if self.progress:
                                step = inputfile.tell()
                                if step != oldstep and random.random() < fupdate:
                                    self.progress.update(step, "Overlap")
                                    oldstep = step
                                
                            line = inputfile.next()
                            parts = line.split()[1:]
                            
                            for j in range(len(parts)):
                                k = float(parts[j])
                                self.fooverlaps[base + symoffset + j, base + symoffset +i] = k
                                self.fooverlaps[base + symoffset + i, base + symoffset + j] = k
                              
                        #blank, blank, column
                        for i in range(3):
                            inputfile.next()
                        
                        base += 4
                                        
                    symoffset += nosymrep
                    base = 0
                        
            if line[48:67] == "SFO MO coefficients":
#extract MO coefficients              
                #read stars and three blank lines
                inputfile.next()
                inputfile.next()
                inputfile.next()
                inputfile.next()
  
                self.logger.info("Creating attribute mocoeffs: array[]")
                
                line = inputfile.next()
                
                if line.find("***** SPIN 1 *****") > 0:
                    beta = 1
                    self.mocoeffs = Numeric.zeros((2, self.nbasis, self.nbasis), "float")
                    
                    #get rid of two blank lines and symmetry label
                    inputfile.next()
                    inputfile.next()
                    sym = inputfile.next()
                    #print sym
                    
                else:
                    beta = 0
                    self.mocoeffs = Numeric.zeros((1, self.nbasis, self.nbasis), "float")
                    
                #get rid of 12 lines of text
                for i in range(10):
                    inputfile.next()
                  
                for spin in range(beta + 1):
                    symoffset = 0
                    base = 0
                    
                    if spin == 1:
                        #read spin, blank, blank, symlabel, blank, text, underline, blank
                        for i in range(8):
                            line = inputfile.next()
                                
                    while symoffset + base < self.nbasis:
                
                        line = inputfile.next()
                        if len(line) < 3:
                            symoffset += base
                            base = 0
                            #print symoffset
                            
                        monumbers = line.split()
                        #print monumbers
                        #get rid of unneeded lines
                        line = inputfile.next()
                        info = line.split()
                        if len(info) > 1: #ie was previous line info about occupation numbers?
                            inputfile.next()
                          
                        row = 0
                        line = inputfile.next()
                        while len(line) > 5:
                           
                            if self.progress:
                                step = inputfile.tell()
                                if step != oldstep and random.random() < fupdate:
                                    self.progress.update(step, "Coefficients")
                                    oldstep = step
            
                            cols = line.split()
                            for i in range(len(cols[1:])):
                                #self.mocoeffs[spin,row+symoffset,i+symoffset+base]=float(cols[i+1])
                                self.mocoeffs[spin, i + symoffset + base, row + symoffset] = float(cols[i + 1])
                            
                            line = inputfile.next()
                            row += 1
                          
                        base += len(cols[1:])
                        
                        
        inputfile.close()

        if self.progress:
            self.progress.update(nstep, "Done")

        if hasattr(self,"geovalues"):
            self.geovalues = Numeric.array(self.geovalues, "f")
        if hasattr(self,"scfenergies"):
            self.scfenergies = Numeric.array(self.scfenergies, "f")
        if hasattr(self,"scfvalues"):
            self.scfvalues = [Numeric.array(x, "f") for x in self.scfvalues]
        if hasattr(self,"scftargets"):
            self.scftargets = Numeric.array(self.scftargets, "f")
        if hasattr(self,"moenergies"):
            self.nmo = len(self.moenergies[0])
        if hasattr(self,"atomcoords"):
            self.atomcoords = Numeric.array(self.atomcoords, "f")

        self.parsed = True

        
if __name__ == "__main__":
    import doctest, adfparser
    doctest.testmod(adfparser, verbose=False)
