# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Test cases for the L{twisted.python.reflect} module.
"""

from __future__ import division, absolute_import

import os
import weakref
from collections import deque

from twisted.python.compat import _PY3
from twisted.trial import unittest
from twisted.trial.unittest import SynchronousTestCase as TestCase
from twisted.python import reflect
from twisted.python.reflect import (
    accumulateMethods, prefixedMethods, prefixedMethodNames,
    addMethodNamesToDict, fullyQualifiedName)
from twisted.python.versions import Version


class Base(object):
    """
    A no-op class which can be used to verify the behavior of
    method-discovering APIs.
    """

    def method(self):
        """
        A no-op method which can be discovered.
        """



class Sub(Base):
    """
    A subclass of a class with a method which can be discovered.
    """



class Separate(object):
    """
    A no-op class with methods with differing prefixes.
    """

    def good_method(self):
        """
        A no-op method which a matching prefix to be discovered.
        """


    def bad_method(self):
        """
        A no-op method with a mismatched prefix to not be discovered.
        """



class AccumulateMethodsTests(TestCase):
    """
    Tests for L{accumulateMethods} which finds methods on a class hierarchy and
    adds them to a dictionary.
    """

    def test_ownClass(self):
        """
        If x is and instance of Base and Base defines a method named method,
        L{accumulateMethods} adds an item to the given dictionary with
        C{"method"} as the key and a bound method object for Base.method value.
        """
        x = Base()
        output = {}
        accumulateMethods(x, output)
        self.assertEqual({"method": x.method}, output)


    def test_baseClass(self):
        """
        If x is an instance of Sub and Sub is a subclass of Base and Base
        defines a method named method, L{accumulateMethods} adds an item to the
        given dictionary with C{"method"} as the key and a bound method object
        for Base.method as the value.
        """
        x = Sub()
        output = {}
        accumulateMethods(x, output)
        self.assertEqual({"method": x.method}, output)


    def test_prefix(self):
        """
        If a prefix is given, L{accumulateMethods} limits its results to
        methods beginning with that prefix.  Keys in the resulting dictionary
        also have the prefix removed from them.
        """
        x = Separate()
        output = {}
        accumulateMethods(x, output, 'good_')
        self.assertEqual({'method': x.good_method}, output)



class PrefixedMethodsTests(TestCase):
    """
    Tests for L{prefixedMethods} which finds methods on a class hierarchy and
    adds them to a dictionary.
    """

    def test_onlyObject(self):
        """
        L{prefixedMethods} returns a list of the methods discovered on an
        object.
        """
        x = Base()
        output = prefixedMethods(x)
        self.assertEqual([x.method], output)


    def test_prefix(self):
        """
        If a prefix is given, L{prefixedMethods} returns only methods named
        with that prefix.
        """
        x = Separate()
        output = prefixedMethods(x, 'good_')
        self.assertEqual([x.good_method], output)



class PrefixedMethodNamesTests(TestCase):
    """
    Tests for L{prefixedMethodNames}.
    """
    def test_method(self):
        """
        L{prefixedMethodNames} returns a list including methods with the given
        prefix defined on the class passed to it.
        """
        self.assertEqual(["method"], prefixedMethodNames(Separate, "good_"))


    def test_inheritedMethod(self):
        """
        L{prefixedMethodNames} returns a list included methods with the given
        prefix defined on base classes of the class passed to it.
        """
        class Child(Separate):
            pass
        self.assertEqual(["method"], prefixedMethodNames(Child, "good_"))



class AddMethodNamesToDictTests(TestCase):
    """
    Tests for L{addMethodNamesToDict}.
    """
    def test_baseClass(self):
        """
        If C{baseClass} is passed to L{addMethodNamesToDict}, only methods which
        are a subclass of C{baseClass} are added to the result dictionary.
        """
        class Alternate(object):
            pass

        class Child(Separate, Alternate):
            def good_alternate(self):
                pass

        result = {}
        addMethodNamesToDict(Child, result, 'good_', Alternate)
        self.assertEqual({'alternate': 1}, result)



class Summer(object):
    """
    A class we look up as part of the LookupsTestCase.
    """

    def reallySet(self):
        """
        Do something.
        """



class LookupsTestCase(TestCase):
    """
    Tests for L{namedClass}, L{namedModule}, and L{namedAny}.
    """

    def test_namedClassLookup(self):
        """
        L{namedClass} should return the class object for the name it is passed.
        """
        self.assertIdentical(
            reflect.namedClass("twisted.test.test_reflect.Summer"),
            Summer)


    def test_namedModuleLookup(self):
        """
        L{namedModule} should return the module object for the name it is
        passed.
        """
        from twisted.python import monkey
        self.assertIdentical(
            reflect.namedModule("twisted.python.monkey"), monkey)


    def test_namedAnyPackageLookup(self):
        """
        L{namedAny} should return the package object for the name it is passed.
        """
        import twisted.python
        self.assertIdentical(
            reflect.namedAny("twisted.python"), twisted.python)


    def test_namedAnyModuleLookup(self):
        """
        L{namedAny} should return the module object for the name it is passed.
        """
        from twisted.python import monkey
        self.assertIdentical(
            reflect.namedAny("twisted.python.monkey"), monkey)


    def test_namedAnyClassLookup(self):
        """
        L{namedAny} should return the class object for the name it is passed.
        """
        self.assertIdentical(
            reflect.namedAny("twisted.test.test_reflect.Summer"),
            Summer)


    def test_namedAnyAttributeLookup(self):
        """
        L{namedAny} should return the object an attribute of a non-module,
        non-package object is bound to for the name it is passed.
        """
        # Note - not assertEqual because unbound method lookup creates a new
        # object every time.  This is a foolishness of Python's object
        # implementation, not a bug in Twisted.
        self.assertEqual(
            reflect.namedAny(
                "twisted.test.test_reflect.Summer.reallySet"),
            Summer.reallySet)


    def test_namedAnySecondAttributeLookup(self):
        """
        L{namedAny} should return the object an attribute of an object which
        itself was an attribute of a non-module, non-package object is bound to
        for the name it is passed.
        """
        self.assertIdentical(
            reflect.namedAny(
                "twisted.test.test_reflect."
                "Summer.reallySet.__doc__"),
            Summer.reallySet.__doc__)


    def test_importExceptions(self):
        """
        Exceptions raised by modules which L{namedAny} causes to be imported
        should pass through L{namedAny} to the caller.
        """
        self.assertRaises(
            ZeroDivisionError,
            reflect.namedAny, "twisted.test.reflect_helper_ZDE")
        # Make sure that there is post-failed-import cleanup
        self.assertRaises(
            ZeroDivisionError,
            reflect.namedAny, "twisted.test.reflect_helper_ZDE")
        self.assertRaises(
            ValueError,
            reflect.namedAny, "twisted.test.reflect_helper_VE")
        # Modules which themselves raise ImportError when imported should
        # result in an ImportError
        self.assertRaises(
            ImportError,
            reflect.namedAny, "twisted.test.reflect_helper_IE")


    def test_attributeExceptions(self):
        """
        If segments on the end of a fully-qualified Python name represents
        attributes which aren't actually present on the object represented by
        the earlier segments, L{namedAny} should raise an L{AttributeError}.
        """
        self.assertRaises(
            AttributeError,
            reflect.namedAny, "twisted.nosuchmoduleintheworld")
        # ImportError behaves somewhat differently between "import
        # extant.nonextant" and "import extant.nonextant.nonextant", so test
        # the latter as well.
        self.assertRaises(
            AttributeError,
            reflect.namedAny, "twisted.nosuch.modulein.theworld")
        self.assertRaises(
            AttributeError,
            reflect.namedAny,
            "twisted.test.test_reflect.Summer.nosuchattribute")


    def test_invalidNames(self):
        """
        Passing a name which isn't a fully-qualified Python name to L{namedAny}
        should result in one of the following exceptions:
         - L{InvalidName}: the name is not a dot-separated list of Python
           objects
         - L{ObjectNotFound}: the object doesn't exist
         - L{ModuleNotFound}: the object doesn't exist and there is only one
           component in the name
        """
        err = self.assertRaises(reflect.ModuleNotFound, reflect.namedAny,
                                'nosuchmoduleintheworld')
        self.assertEqual(str(err), "No module named 'nosuchmoduleintheworld'")

        # This is a dot-separated list, but it isn't valid!
        err = self.assertRaises(reflect.ObjectNotFound, reflect.namedAny,
                                "@#$@(#.!@(#!@#")
        self.assertEqual(str(err), "'@#$@(#.!@(#!@#' does not name an object")

        err = self.assertRaises(reflect.ObjectNotFound, reflect.namedAny,
                                "tcelfer.nohtyp.detsiwt")
        self.assertEqual(
            str(err),
            "'tcelfer.nohtyp.detsiwt' does not name an object")

        err = self.assertRaises(reflect.InvalidName, reflect.namedAny, '')
        self.assertEqual(str(err), 'Empty module name')

        for invalidName in ['.twisted', 'twisted.', 'twisted..python']:
            err = self.assertRaises(
                reflect.InvalidName, reflect.namedAny, invalidName)
            self.assertEqual(
                str(err),
                "name must be a string giving a '.'-separated list of Python "
                "identifiers, not %r" % (invalidName,))


    def test_requireModuleImportError(self):
        """
        When module import fails with ImportError it returns the specified
        default value.
        """
        for name in ['nosuchmtopodule', 'no.such.module']:
            default = object()

            result = reflect.requireModule(name, default=default)

            self.assertIs(result, default)


    def test_requireModuleOtherError(self):
        """
        When module import fails with error, other than ImportError, it
        raises that error.
        """
        self.assertRaises(
            ValueError,
            reflect.requireModule, 'twisted..python',
            )


    def test_requireModuleDefaultNone(self):
        """
        When module import fails it returns C{None} by default.
        """
        result = reflect.requireModule('no.such.module')

        self.assertIs(None, result)



    def test_requireModuleRequestedImport(self):
        """
        When module import succeed it returns the module and not the default
        value.
        """
        from twisted.python import monkey
        default = object()

        self.assertIs(
            reflect.requireModule('twisted.python.monkey', default=default),
            monkey,
            )



class Breakable(object):

    breakRepr = False
    breakStr = False

    def __str__(self):
        if self.breakStr:
            raise RuntimeError("str!")
        else:
            return '<Breakable>'


    def __repr__(self):
        if self.breakRepr:
            raise RuntimeError("repr!")
        else:
            return 'Breakable()'



class BrokenType(Breakable, type):
    breakName = False

    def get___name__(self):
        if self.breakName:
            raise RuntimeError("no name")
        return 'BrokenType'
    __name__ = property(get___name__)



BTBase = BrokenType('BTBase', (Breakable,),
                    {"breakRepr": True,
                     "breakStr": True})



class NoClassAttr(Breakable):
    __class__ = property(lambda x: x.not_class)



class SafeRepr(TestCase):
    """
    Tests for L{reflect.safe_repr} function.
    """

    def test_workingRepr(self):
        """
        L{reflect.safe_repr} produces the same output as C{repr} on a working
        object.
        """
        x = [1, 2, 3]
        self.assertEqual(reflect.safe_repr(x), repr(x))


    def test_brokenRepr(self):
        """
        L{reflect.safe_repr} returns a string with class name, address, and
        traceback when the repr call failed.
        """
        b = Breakable()
        b.breakRepr = True
        bRepr = reflect.safe_repr(b)
        self.assertIn("Breakable instance at 0x", bRepr)
        # Check that the file is in the repr, but without the extension as it
        # can be .py/.pyc
        self.assertIn(os.path.splitext(__file__)[0], bRepr)
        self.assertIn("RuntimeError: repr!", bRepr)


    def test_brokenStr(self):
        """
        L{reflect.safe_repr} isn't affected by a broken C{__str__} method.
        """
        b = Breakable()
        b.breakStr = True
        self.assertEqual(reflect.safe_repr(b), repr(b))


    def test_brokenClassRepr(self):
        class X(BTBase):
            breakRepr = True
        reflect.safe_repr(X)
        reflect.safe_repr(X())


    def test_brokenReprIncludesID(self):
        """
        C{id} is used to print the ID of the object in case of an error.

        L{safe_repr} includes a traceback after a newline, so we only check
        against the first line of the repr.
        """
        class X(BTBase):
            breakRepr = True

        xRepr = reflect.safe_repr(X)
        xReprExpected = ('<BrokenType instance at 0x%x with repr error:'
                         % (id(X),))
        self.assertEqual(xReprExpected, xRepr.split('\n')[0])


    def test_brokenClassStr(self):
        class X(BTBase):
            breakStr = True
        reflect.safe_repr(X)
        reflect.safe_repr(X())


    def test_brokenClassAttribute(self):
        """
        If an object raises an exception when accessing its C{__class__}
        attribute, L{reflect.safe_repr} uses C{type} to retrieve the class
        object.
        """
        b = NoClassAttr()
        b.breakRepr = True
        bRepr = reflect.safe_repr(b)
        self.assertIn("NoClassAttr instance at 0x", bRepr)
        self.assertIn(os.path.splitext(__file__)[0], bRepr)
        self.assertIn("RuntimeError: repr!", bRepr)


    def test_brokenClassNameAttribute(self):
        """
        If a class raises an exception when accessing its C{__name__} attribute
        B{and} when calling its C{__str__} implementation, L{reflect.safe_repr}
        returns 'BROKEN CLASS' instead of the class name.
        """
        class X(BTBase):
            breakName = True
        xRepr = reflect.safe_repr(X())
        self.assertIn("<BROKEN CLASS AT 0x", xRepr)
        self.assertIn(os.path.splitext(__file__)[0], xRepr)
        self.assertIn("RuntimeError: repr!", xRepr)



class SafeStr(TestCase):
    """
    Tests for L{reflect.safe_str} function.
    """

    def test_workingStr(self):
        x = [1, 2, 3]
        self.assertEqual(reflect.safe_str(x), str(x))


    def test_brokenStr(self):
        b = Breakable()
        b.breakStr = True
        reflect.safe_str(b)


    def test_brokenRepr(self):
        b = Breakable()
        b.breakRepr = True
        reflect.safe_str(b)


    def test_brokenClassStr(self):
        class X(BTBase):
            breakStr = True
        reflect.safe_str(X)
        reflect.safe_str(X())


    def test_brokenClassRepr(self):
        class X(BTBase):
            breakRepr = True
        reflect.safe_str(X)
        reflect.safe_str(X())


    def test_brokenClassAttribute(self):
        """
        If an object raises an exception when accessing its C{__class__}
        attribute, L{reflect.safe_str} uses C{type} to retrieve the class
        object.
        """
        b = NoClassAttr()
        b.breakStr = True
        bStr = reflect.safe_str(b)
        self.assertIn("NoClassAttr instance at 0x", bStr)
        self.assertIn(os.path.splitext(__file__)[0], bStr)
        self.assertIn("RuntimeError: str!", bStr)


    def test_brokenClassNameAttribute(self):
        """
        If a class raises an exception when accessing its C{__name__} attribute
        B{and} when calling its C{__str__} implementation, L{reflect.safe_str}
        returns 'BROKEN CLASS' instead of the class name.
        """
        class X(BTBase):
            breakName = True
        xStr = reflect.safe_str(X())
        self.assertIn("<BROKEN CLASS AT 0x", xStr)
        self.assertIn(os.path.splitext(__file__)[0], xStr)
        self.assertIn("RuntimeError: str!", xStr)



class FilenameToModule(TestCase):
    """
    Test L{filenameToModuleName} detection.
    """

    def setUp(self):
        self.path = os.path.join(self.mktemp(), "fakepackage", "test")
        os.makedirs(self.path)
        with open(os.path.join(self.path, "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(os.path.dirname(self.path), "__init__.py"),
                  "w") as f:
            f.write("")


    def test_directory(self):
        """
        L{filenameToModuleName} returns the correct module (a package) given a
        directory.
        """
        module = reflect.filenameToModuleName(self.path)
        self.assertEqual(module, 'fakepackage.test')
        module = reflect.filenameToModuleName(self.path + os.path.sep)
        self.assertEqual(module, 'fakepackage.test')


    def test_file(self):
        """
        L{filenameToModuleName} returns the correct module given the path to
        its file.
        """
        module = reflect.filenameToModuleName(
            os.path.join(self.path, 'test_reflect.py'))
        self.assertEqual(module, 'fakepackage.test.test_reflect')


    def test_bytes(self):
        """
        L{filenameToModuleName} returns the correct module given a C{bytes}
        path to its file.
        """
        module = reflect.filenameToModuleName(
            os.path.join(self.path.encode("utf-8"), b'test_reflect.py'))
        # Module names are always native string:
        self.assertEqual(module, 'fakepackage.test.test_reflect')



class FullyQualifiedNameTests(TestCase):
    """
    Test for L{fullyQualifiedName}.
    """

    def _checkFullyQualifiedName(self, obj, expected):
        """
        Helper to check that fully qualified name of C{obj} results to
        C{expected}.
        """
        self.assertEqual(fullyQualifiedName(obj), expected)


    def test_package(self):
        """
        L{fullyQualifiedName} returns the full name of a package and a
        subpackage.
        """
        import twisted
        self._checkFullyQualifiedName(twisted, 'twisted')
        import twisted.python
        self._checkFullyQualifiedName(twisted.python, 'twisted.python')


    def test_module(self):
        """
        L{fullyQualifiedName} returns the name of a module inside a a package.
        """
        import twisted.python.compat
        self._checkFullyQualifiedName(
            twisted.python.compat, 'twisted.python.compat')


    def test_class(self):
        """
        L{fullyQualifiedName} returns the name of a class and its module.
        """
        self._checkFullyQualifiedName(
            FullyQualifiedNameTests,
            '%s.FullyQualifiedNameTests' % (__name__,))


    def test_function(self):
        """
        L{fullyQualifiedName} returns the name of a function inside its module.
        """
        self._checkFullyQualifiedName(
            fullyQualifiedName, "twisted.python.reflect.fullyQualifiedName")


    def test_boundMethod(self):
        """
        L{fullyQualifiedName} returns the name of a bound method inside its
        class and its module.
        """
        self._checkFullyQualifiedName(
            self.test_boundMethod,
            "%s.%s.test_boundMethod" % (__name__, self.__class__.__name__))


    def test_unboundMethod(self):
        """
        L{fullyQualifiedName} returns the name of an unbound method inside its
        class and its module.
        """
        self._checkFullyQualifiedName(
            self.__class__.test_unboundMethod,
            "%s.%s.test_unboundMethod" % (__name__, self.__class__.__name__))


class ObjectGrep(unittest.TestCase):
    if _PY3:
        # This is to be removed when fixing #6986
        skip = "twisted.python.reflect.objgrep hasn't been ported to Python 3"


    def test_dictionary(self):
        """
        Test references search through a dictionnary, as a key or as a value.
        """
        o = object()
        d1 = {None: o}
        d2 = {o: None}

        self.assertIn("[None]", reflect.objgrep(d1, o, reflect.isSame))
        self.assertIn("{None}", reflect.objgrep(d2, o, reflect.isSame))

    def test_list(self):
        """
        Test references search through a list.
        """
        o = object()
        L = [None, o]

        self.assertIn("[1]", reflect.objgrep(L, o, reflect.isSame))

    def test_tuple(self):
        """
        Test references search through a tuple.
        """
        o = object()
        T = (o, None)

        self.assertIn("[0]", reflect.objgrep(T, o, reflect.isSame))

    def test_instance(self):
        """
        Test references search through an object attribute.
        """
        class Dummy:
            pass
        o = object()
        d = Dummy()
        d.o = o

        self.assertIn(".o", reflect.objgrep(d, o, reflect.isSame))

    def test_weakref(self):
        """
        Test references search through a weakref object.
        """
        class Dummy:
            pass
        o = Dummy()
        w1 = weakref.ref(o)

        self.assertIn("()", reflect.objgrep(w1, o, reflect.isSame))

    def test_boundMethod(self):
        """
        Test references search through method special attributes.
        """
        class Dummy:
            def dummy(self):
                pass
        o = Dummy()
        m = o.dummy

        self.assertIn(".__self__",
                      reflect.objgrep(m, m.__self__, reflect.isSame))
        self.assertIn(".__self__.__class__",
                      reflect.objgrep(m, m.__self__.__class__, reflect.isSame))
        self.assertIn(".__func__",
                      reflect.objgrep(m, m.__func__, reflect.isSame))

    def test_everything(self):
        """
        Test references search using complex set of objects.
        """
        class Dummy:
            def method(self):
                pass

        o = Dummy()
        D1 = {(): "baz", None: "Quux", o: "Foosh"}
        L = [None, (), D1, 3]
        T = (L, {}, Dummy())
        D2 = {0: "foo", 1: "bar", 2: T}
        i = Dummy()
        i.attr = D2
        m = i.method
        w = weakref.ref(m)

        self.assertIn("().__self__.attr[2][0][2]{'Foosh'}",
                      reflect.objgrep(w, o, reflect.isSame))

    def test_depthLimit(self):
        """
        Test the depth of references search.
        """
        a = []
        b = [a]
        c = [a, b]
        d = [a, c]

        self.assertEqual(['[0]'], reflect.objgrep(d, a, reflect.isSame, maxDepth=1))
        self.assertEqual(['[0]', '[1][0]'], reflect.objgrep(d, a, reflect.isSame, maxDepth=2))
        self.assertEqual(['[0]', '[1][0]', '[1][1][0]'], reflect.objgrep(d, a, reflect.isSame, maxDepth=3))


    def test_deque(self):
        """
        Test references search through a deque object.
        """
        o = object()
        D = deque()
        D.append(None)
        D.append(o)

        self.assertIn("[1]", reflect.objgrep(D, o, reflect.isSame))


class GetClass(unittest.TestCase):
    if _PY3:
        oldClassNames = ['type']
    else:
        oldClassNames = ['class', 'classobj']

    def testOld(self):
        class OldClass:
            pass
        old = OldClass()
        self.assertIn(reflect.getClass(OldClass).__name__, self.oldClassNames)
        self.assertEqual(reflect.getClass(old).__name__, 'OldClass')

    def testNew(self):
        class NewClass(object):
            pass
        new = NewClass()
        self.assertEqual(reflect.getClass(NewClass).__name__, 'type')
        self.assertEqual(reflect.getClass(new).__name__, 'NewClass')


if not _PY3:
    # The functions tested below are deprecated but still used by external
    # projects like Nevow 0.10. They are not going to be ported to Python 3
    # (hence the condition above) and will be removed as soon as no project used
    # by Twisted will depend on these functions. Also, have a look at the
    # comments related to those functions in twisted.python.reflect.
    class DeprecationTestCase(unittest.TestCase):
        """
        Test deprecations in twisted.python.reflect
        """

        def test_allYourBase(self):
            """
            Test deprecation of L{reflect.allYourBase}. See #5481 for removal.
            """
            self.callDeprecated(
                (Version("Twisted", 11, 0, 0), "inspect.getmro"),
                reflect.allYourBase, DeprecationTestCase)


        def test_accumulateBases(self):
            """
            Test deprecation of L{reflect.accumulateBases}. See #5481 for removal.
            """
            l = []
            self.callDeprecated(
                (Version("Twisted", 11, 0, 0), "inspect.getmro"),
                reflect.accumulateBases, DeprecationTestCase, l, None)


        def test_getcurrent(self):
            """
            Test deprecation of L{reflect.getcurrent}.
            """

            class C:
                pass

            self.callDeprecated(
                Version("Twisted", 14, 0, 0),
                reflect.getcurrent, C)


        def test_isinst(self):
            """
            Test deprecation of L{reflect.isinst}.
            """

            self.callDeprecated(
                (Version("Twisted", 14, 0, 0), "isinstance"),
                reflect.isinst, object(), object)
