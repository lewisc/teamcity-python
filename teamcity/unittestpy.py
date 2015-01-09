# coding=utf-8
import traceback
import sys
from unittest import TestResult
import datetime
import re

from teamcity.messages import TeamcityServiceMessages


def _is_string(obj):
    if sys.version_info >= (3, 0):
        return isinstance(obj, str)
    else:
        return isinstance(obj, basestring)


# Added *k to some methods to get compatibility with nosetests
class TeamcityTestResult(TestResult):
    def __init__(self, stream=sys.stdout):
        super(TeamcityTestResult, self).__init__()

        self.output = stream
        self.test_started_datetime_map = {}

        self.create_messages()

    def create_messages(self):
        self.messages = TeamcityServiceMessages(self.output)

    def formatErr(self, err):
        try:
            exctype, value, tb = err
            return ''.join(traceback.format_exception(exctype, value, tb))
        except:
            tb = traceback.format_exc()
            return "*FAILED TO GET TRACEBACK*: " + tb

    def _class_fullname(self, o):
        module = o.__class__.__module__
        if module is None or module == str.__class__.__module__:
            return o.__class__.__name__
        return module + '.' + o.__class__.__name__

    def is_doctest_class_name(self, fqn):
        return fqn == "doctest.DocTestCase"

    def get_test_id(self, test):
        # Force test_id for doctests
        if not self.is_doctest_class_name(self._class_fullname(test)):
            desc = test.shortDescription()
            if desc and desc != test.id():
                return "%s (%s)" % (test.id(), desc)

        return test.id()

    def addSuccess(self, test, *k):
        super(TeamcityTestResult, self).addSuccess(test)

    def addExpectedFailure(self, test, err):
        # workaround nose bug on python 3
        if _is_string(err[1]):
            err = (err[0], Exception(err[1]), err[2])

        super(TeamcityTestResult, self).addExpectedFailure(test, err)

        err = self.formatErr(err)

        self.messages.testIgnored(self.get_test_id(test), message="Expected failure: " + err)

    def addSkip(self, test, reason="", *k):
        if sys.version_info >= (2, 7):
            super(TeamcityTestResult, self).addSkip(test, reason)

        self.messages.testIgnored(self.get_test_id(test), message="Skipped" + ((": " + reason) if reason else ""))

    def addUnexpectedSuccess(self, test):
        super(TeamcityTestResult, self).addUnexpectedSuccess(test)

        self.messages.testFailed(self.get_test_id(test), message='Failure',
                                 details="Test should not succeed since it's marked with @unittest.expectedFailure")

    def addError(self, test, err, *k):
        # workaround nose bug on python 3
        if _is_string(err[1]):
            err = (err[0], Exception(err[1]), err[2])

        super(TeamcityTestResult, self).addError(test, err)

        err = self.formatErr(err)

        if self._class_fullname(test) == "unittest.suite._ErrorHolder":
            # This is a standalone error

            test_name = test.id()
            # patch setUpModule (__main__) -> __main__.setUpModule
            test_name = re.sub(r'^(.*) \((.*)\)$', r'\2.\1', test_name)

            self.messages.testStarted(test_name)
            self.messages.testFailed(test_name, message='Failure', details=err)
            self.messages.testFinished(test_name)
            return

        self.messages.testFailed(self.get_test_id(test), message='Error', details=err)

    def addFailure(self, test, err, *k):
        # workaround nose bug on python 3
        if _is_string(err[1]):
            err = (err[0], Exception(err[1]), err[2])

        super(TeamcityTestResult, self).addFailure(test, err)

        err = self.formatErr(err)
        self.messages.testFailed(self.get_test_id(test), message='Failure', details=err)

    def startTest(self, test):
        test_id = self.get_test_id(test)

        self.test_started_datetime_map[test_id] = datetime.datetime.now()
        self.messages.testStarted(test_id)

    def stopTest(self, test):
        test_id = self.get_test_id(test)

        time_diff = datetime.datetime.now() - self.test_started_datetime_map[test_id]
        self.messages.testFinished(test_id, time_diff)


class TeamcityTestRunner(object):
    def __init__(self, stream=sys.stderr, *args, **kwargs):
        self.stream = stream

    def _makeResult(self):
        return TeamcityTestResult(self.stream)

    def run(self, test):
        result = self._makeResult()
        test(result)
        return result


if __name__ == '__main__':
    from unittest import main

    main(module=None, testRunner=TeamcityTestRunner())
