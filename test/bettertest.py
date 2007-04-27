import unittest

# If numpy is not installed, try to import Numeric instead.
try:
    import numpy
except ImportError:
    import Numeric as numpy
    numpy.dtype = numpy.typecode


class TestCase(unittest.TestCase):
    """Create a class with extra 'asserts' for testing numerical data.

    It is not possible to test equality of numpy arrays using assertEquals().
    Instead, use assertArrayEquals() as defined below. For the original solution see:
    http://mail.python.org/pipermail/python-list/2005-November/311235.html

    Also, for testing near equality of floats use assertInside.
    (Taken from Python Cookbook 2nd Ed. Recipe 8.11)
    """
    def assertInside(self,first,second,error,msg=None):
        """Fail if the second number isn't within a certain error of the first."""
        if not (second-error) < first < (second+error):
            raise self.failureException, (msg or '%r != %r (+-%r)' % (first,second,error))

    def assertArrayEquals(self,first,second,msg=None):
        """Fails unless two numpy arrays are identical."""
        errormsg = None
        if not first.shape==second.shape:
            errormsg = "Shapes are different: %s != %s" % (first.shape, second.shape)
        if not first.dtype==second.dtype:
            errormsg = "Typecodes are differnts: %s != %s" % (first.dtype, second.dtype)
        if not numpy.alltrue(first==second):
            errormsg = "Not equal: %s != %s" % (first, second)
        if errormsg:
            raise self.failureException, (msg or errormsg)
