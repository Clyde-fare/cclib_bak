import os
import Numeric
import unittest

from testall import getfile
from cclib.parser import ADF, GAMESS, Gaussian, Jaguar, GAMESSUK
from cclib.parser.utils import PeriodicTable

import bettertest

class GenericCoreTest(bettertest.TestCase):
    """Core electrons"""
    def testcorrect(self):
        """Is coreelectrons equal to what it should be?"""
        pt = PeriodicTable()
        ans = []
        for x in self.data.atomnos:
            ans.append(self.coredict[pt.element[x]])
        ans = Numeric.array(ans, "i")
        self.assertArrayEquals(self.data.coreelectrons, ans)

class GaussianCoreTest(GenericCoreTest):
    def setUp(self):
        self.data = data[0]
        self.coredict = {'Mo': 28, 'O':0, 'Cl':10}

class ADFCoreTest(GenericCoreTest):
    def setUp(self):
        self.data = data[1]
        self.coredict = {'Mo': 36}


names = [ "Gaussian", "ADF" ]
tests = [ GaussianCoreTest, ADFCoreTest ]
data = [getfile(Gaussian, "basicGaussian03","Mo4OCl4-sp.log"),
        getfile(ADF, "basicADF2004.01","mo_sp.adfout"),
        ]
              
if __name__=="__main__":
    total = errors = failures = 0

    for name,test in zip(names,tests):
        print "\n**** Testing %s ****" % name
        myunittest = unittest.makeSuite(test)
        a = unittest.TextTestRunner(verbosity=2).run(myunittest)
        total += a.testsRun
        errors += len(a.errors)
        failures += len(a.failures)

    print "\n\n********* SUMMARY OF MP TEST **************"
    print "TOTAL: %d\tPASSED: %d\tFAILED: %d\tERRORS: %d" % (total,total-(errors+failures),failures,errors)
