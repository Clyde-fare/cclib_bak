__revision__ = "$Revision$"

import os, unittest

# If numpy is not installed, try to import Numeric instead.
try:
    import numpy
except ImportError:
    import Numeric as numpy

import bettertest
from testall import gettestdata


class GenericCITest(bettertest.TestCase):
    """CI calculations."""
    nstates = 0
    
    def testnumberofstates(self):
        """ Are there nstate elements in etenergies/etsecs/etsyms/etoscs?"""
        self.assertEqual(len(self.data.etenergies), self.nstates)
        self.assertEqual(len(self.data.etsecs), self.nstates)
        self.assertEqual(len(self.data.etsyms), self.nstates)
        self.assertEqual(len(self.data.etoscs), self.nstates)

    
    def testetenergies(self):
        """ Are transition energies positive and rising?"""
        self.failUnless(numpy.alltrue(self.data.etenergies > 0.0))
        changes = self.data.etenergies[1:] - self.data.etenergies[:-1]
        self.failUnless(numpy.alltrue(changes > 0.0))

class GenericCISTest(GenericCITest):
    """CIS calculations."""
    
class GenericCISWaterTest(GenericCISTest):
    """CIS(RHF) calculations of water (STO-3G)."""
    # First four singlet/triplet state excitation energies [cm-1].
    # Based on output in GAMESS test.
    etenergies0 = numpy.array([98614.56, 114906.59, 127948.12, 146480.64])
    etenergies1 = numpy.array([82085.34,  98999.11, 104077.89, 113978.37])
    # First four singlet/triplet state excitation orbitals and coefficients.
    # Tuples: (from MO, to MO, coefficient) - don't need spin indices.
    # Based on output in GAMESS test (using the "dets" algorithm).
    # Note that only coefficients larger than 0.1 are included here, as
    #   the Gaussian test does not contain smaller ones.
    # The simple example of water should yield the same first 4 states in all programs.
    # Note that the GAMESS test "water_cis_dets" calculates also triplet states,
    #  but the resulting transition dipoles and oscillator strengths are not correct.
    etsecs0 = [ [(4, 5, -0.70710678)],
                [(4, 6, -0.70710678)],
                [(3, 5,  0.68368723)],
                [(2, 5,  0.31163855), (3, 6, -0.63471970)] ]
    etsecs1 = [ [(4, 5,  0.70710678)],
                [(2, 6, -0.16333506), (3, 6, -0.68422741)],
                [(4, 6,  0.70710678)],
                [(2, 5, -0.37899667), (3, 6, -0.59602876)] ]
                
    def testetenergiesvalues(self):
        """ Are etenergies within 50cm-1 of the correct values?"""
        indices0 = [i for i in range(self.nstates) if self.data.etsyms[i][0] == "S"]
        indices1 = [i for i in range(self.nstates) if self.data.etsyms[i][0] == "T"]
        singlets = [self.data.etenergies[i] for i in indices0]
        triplets = [self.data.etenergies[i] for i in indices1]
        # All programs do singlets.
        singletdiff = singlets[:4] - self.etenergies0
        self.failUnless(numpy.alltrue(singletdiff < 50))
        # Not all programs do triplets (i.e. Jaguar).
        if len(triplets) >= 4:
            tripletdiff = triplets[:4] - self.etenergies1
            self.failUnless(numpy.alltrue(tripletdiff < 50))

    def testetsecsvalues(self):
        """ Are etsecs correct and coefficients within 0.0005 of the correct values?"""
        indices0 = [i for i in range(self.nstates) if self.data.etsyms[i][0] == "S"]
        indices1 = [i for i in range(self.nstates) if self.data.etsyms[i][0] == "T"]
        singlets = [self.data.etsecs[i] for i in indices0]
        triplets = [self.data.etsecs[i] for i in indices1]
        # All programs do singlets.
        found = False
        for i in range(4):
            for exc in self.etsecs0[i]:
                for s in singlets[i]:
                    if s[0][0] == exc[0] and s[1][0] == exc[1]:
                        found = True
                        self.assertInside(abs(s[2]), abs(exc[2]), 0.0005)
        if not found:
            self.fail("Excitation %i->%s not found (singlet state %i)" %(exc[0], exc[1], i))
        # Not all programs do triplets (i.e. Jaguar).
        if len(triplets) >= 4:
            found = False
            for i in range(4):
                for exc in self.etsecs1[i]:
                    for s in triplets[i]:
                        if s[0][0] == exc[0] and s[1][0] == exc[1]:
                            found = True
                            self.assertInside(abs(s[2]), abs(exc[2]), 0.0005)
            if not found:
                self.fail("Excitation %i->%s not found (triplet state %i)" %(exc[0], exc[1], i))

class GAMESSUSCISTest(GenericCISWaterTest):
    def setUp(self):
        self.data = testdata[self.__class__.__name__]["data"]
        self.nstates = 5

class GaussianCISTest(GenericCISWaterTest):
    def setUp(self):
        self.data = testdata[self.__class__.__name__]["data"]
        self.nstates = 10

class Jaguar65CISTest(GenericCISWaterTest):
    def setUp(self):
        self.data = testdata[self.__class__.__name__]["data"]
        self.nstates = 5

# Load test data using information in file.
testdata = gettestdata(module="CI")
             
if __name__=="__main__":
    total = errors = failures = 0
    for test in testdata:
        module = testdata[test]["module"]
        print "\n**** test%s for %s ****" %(module, '/'.join(testdata[test]["location"]))
        test = eval(test)
        myunittest = unittest.makeSuite(test)
        a = unittest.TextTestRunner(verbosity=2).run(myunittest)
        total += a.testsRun
        errors += len(a.errors)
        failures += len(a.failures)

    print "\n\n********* SUMMARY OF CI TEST **************"
    print "TOTAL: %d\tPASSED: %d\tFAILED: %d\tERRORS: %d" % (total,total-(errors+failures),failures,errors)
