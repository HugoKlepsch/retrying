# Copyright 2013 Ray Holder
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import random
import time
import unittest

from retrying import RetryError
from retrying import Retrying
from retrying import retry


class TestStopConditions(unittest.TestCase):
    def test_never_stop(self):
        r = Retrying()
        self.assertFalse(r.stop(3, 6546))

    def test_stop_after_attempt(self):
        r = Retrying(stop_max_attempt_number=3)
        self.assertFalse(r.stop(2, 6546))
        self.assertTrue(r.stop(3, 6546))
        self.assertTrue(r.stop(4, 6546))

    def test_stop_after_delay(self):
        r = Retrying(stop_max_delay=1000)
        self.assertFalse(r.stop(2, 999))
        self.assertTrue(r.stop(2, 1000))
        self.assertTrue(r.stop(2, 1001))

    def test_legacy_explicit_stop_type(self):
        Retrying(stop="stop_after_attempt")

    def test_stop_func(self):
        r = Retrying(stop_func=lambda attempt, delay: attempt == delay)
        self.assertFalse(r.stop(1, 3))
        self.assertFalse(r.stop(100, 99))
        self.assertTrue(r.stop(101, 101))


class TestWaitConditions(unittest.TestCase):
    def test_no_sleep(self):
        r = Retrying()
        self.assertEqual(0, r.wait(18, 9879))

    def test_fixed_sleep(self):
        r = Retrying(wait_fixed=1000)
        self.assertEqual(1000, r.wait(12, 6546))

    def test_incrementing_sleep(self):
        r = Retrying(wait_incrementing_start=500, wait_incrementing_increment=100)
        self.assertEqual(500, r.wait(1, 6546))
        self.assertEqual(600, r.wait(2, 6546))
        self.assertEqual(700, r.wait(3, 6546))

    def test_random_sleep(self):
        r = Retrying(wait_random_min=1000, wait_random_max=2000)
        times = set()
        times.add(r.wait(1, 6546))
        times.add(r.wait(1, 6546))
        times.add(r.wait(1, 6546))
        times.add(r.wait(1, 6546))

        # this is kind of non-deterministic...
        self.assertTrue(len(times) > 1)
        for t in times:
            self.assertTrue(t >= 1000)
            self.assertTrue(t <= 2000)

    def test_random_sleep_without_min(self):
        r = Retrying(wait_random_max=2000)
        times = set()
        times.add(r.wait(1, 6546))
        times.add(r.wait(1, 6546))
        times.add(r.wait(1, 6546))
        times.add(r.wait(1, 6546))

        # this is kind of non-deterministic...
        self.assertTrue(len(times) > 1)
        for t in times:
            self.assertTrue(t >= 0)
            self.assertTrue(t <= 2000)

    def test_exponential(self):
        r = Retrying(wait_exponential_max=100000)
        self.assertEqual(r.wait(1, 0), 2)
        self.assertEqual(r.wait(2, 0), 4)
        self.assertEqual(r.wait(3, 0), 8)
        self.assertEqual(r.wait(4, 0), 16)
        self.assertEqual(r.wait(5, 0), 32)
        self.assertEqual(r.wait(6, 0), 64)

    def test_exponential_with_max_wait(self):
        r = Retrying(wait_exponential_max=40)
        self.assertEqual(r.wait(1, 0), 2)
        self.assertEqual(r.wait(2, 0), 4)
        self.assertEqual(r.wait(3, 0), 8)
        self.assertEqual(r.wait(4, 0), 16)
        self.assertEqual(r.wait(5, 0), 32)
        self.assertEqual(r.wait(6, 0), 40)
        self.assertEqual(r.wait(7, 0), 40)
        self.assertEqual(r.wait(50, 0), 40)

    def test_exponential_with_max_wait_and_multiplier(self):
        r = Retrying(wait_exponential_max=50000, wait_exponential_multiplier=1000)
        self.assertEqual(r.wait(1, 0), 2000)
        self.assertEqual(r.wait(2, 0), 4000)
        self.assertEqual(r.wait(3, 0), 8000)
        self.assertEqual(r.wait(4, 0), 16000)
        self.assertEqual(r.wait(5, 0), 32000)
        self.assertEqual(r.wait(6, 0), 50000)
        self.assertEqual(r.wait(7, 0), 50000)
        self.assertEqual(r.wait(50, 0), 50000)

    def test_legacy_explicit_wait_type(self):
        Retrying(wait="exponential_sleep")

    def test_wait_func(self):
        r = Retrying(wait_func=lambda attempt, delay: attempt * delay)
        self.assertEqual(r.wait(1, 5), 5)
        self.assertEqual(r.wait(2, 11), 22)
        self.assertEqual(r.wait(10, 100), 1000)


class NoneReturnUntilAfterCount:
    """
    This class holds counter state for invoking a method several times in a row.
    """

    def __init__(self, count):
        self.counter = 0
        self.count = count

    def go(self):
        """
        Return None until after count threshold has been crossed, then return True.
        """
        if self.counter < self.count:
            self.counter += 1
            return None
        return True


class NoIOErrorAfterCount:
    """
    This class holds counter state for invoking a method several times in a row.
    """

    def __init__(self, count):
        self.counter = 0
        self.count = count

    def go(self):
        """
        Raise an IOError until after count threshold has been crossed, then return True.
        """
        if self.counter < self.count:
            self.counter += 1
            raise IOError("Hi there, I'm an IOError")
        return True


class NoNameErrorAfterCount:
    """
    This class holds counter state for invoking a method several times in a row.
    """

    def __init__(self, count):
        self.counter = 0
        self.count = count

    def go(self):
        """
        Raise a NameError until after count threshold has been crossed, then return True.
        """
        if self.counter < self.count:
            self.counter += 1
            raise NameError("Hi there, I'm a NameError")
        return True


class CustomError(Exception):
    """
    This is a custom exception class. Note that For Python 2.x, we don't
    strictly need to extend BaseException, however, Python 3.x will complain.
    While this test suite won't run correctly under Python 3.x without
    extending from the Python exception hierarchy, the actual module code is
    backwards compatible Python 2.x and will allow for cases where exception
    classes don't extend from the hierarchy.
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class NoCustomErrorAfterCount:
    """
    This class holds counter state for invoking a method several times in a row.
    """

    def __init__(self, count):
        self.counter = 0
        self.count = count

    def go(self):
        """
        Raise a CustomError until after count threshold has been crossed, then return True.
        """
        if self.counter < self.count:
            self.counter += 1
            derived_message = "This is a Custom exception class"
            raise CustomError(derived_message)
        return True


def retry_if_result_none(result):
    return result is None


def retry_if_exception_of_type(retryable_types):
    def retry_if_exception_these_types(exception):
        print(f"Detected Exception of type: {str(type(exception))}")
        return isinstance(exception, retryable_types)

    return retry_if_exception_these_types


def current_time_ms():
    return int(round(time.time() * 1000))


@retry(wait_fixed=50, retry_on_result=retry_if_result_none)
def _retryable_test_with_wait(thing):
    return thing.go()


@retry(stop_max_attempt_number=3, retry_on_result=retry_if_result_none)
def _retryable_test_with_stop(thing):
    return thing.go()


@retry(retry_on_exception=(IOError,))
def _retryable_test_with_exception_type_io(thing):
    return thing.go()


@retry(retry_on_exception=retry_if_exception_of_type(IOError), wrap_exception=True)
def _retryable_test_with_exception_type_io_wrap(thing):
    return thing.go()


@retry(stop_max_attempt_number=3, retry_on_exception=(IOError,))
def _retryable_test_with_exception_type_io_attempt_limit(thing):
    return thing.go()


@retry(stop_max_attempt_number=3, retry_on_exception=(IOError,), wrap_exception=True)
def _retryable_test_with_exception_type_io_attempt_limit_wrap(thing):
    return thing.go()


@retry
def _retryable_default(thing):
    return thing.go()


@retry()
def _retryable_default_f(thing):
    return thing.go()


@retry(retry_on_exception=retry_if_exception_of_type(CustomError))
def _retryable_test_with_exception_type_custom(thing):
    return thing.go()


@retry(retry_on_exception=retry_if_exception_of_type(CustomError), wrap_exception=True)
def _retryable_test_with_exception_type_custom_wrap(thing):
    return thing.go()


@retry(
    stop_max_attempt_number=3,
    retry_on_exception=retry_if_exception_of_type(CustomError),
)
def _retryable_test_with_exception_type_custom_attempt_limit(thing):
    return thing.go()


@retry(
    stop_max_attempt_number=3,
    retry_on_exception=retry_if_exception_of_type(CustomError),
    wrap_exception=True,
)
def _retryable_test_with_exception_type_custom_attempt_limit_wrap(thing):
    return thing.go()


class TestDecoratorWrapper(unittest.TestCase):
    def test_with_wait(self):
        start = current_time_ms()
        result = _retryable_test_with_wait(NoneReturnUntilAfterCount(5))
        t = current_time_ms() - start
        self.assertTrue(t >= 250)
        self.assertTrue(result)

    def test_with_stop_on_return_value(self):
        try:
            _retryable_test_with_stop(NoneReturnUntilAfterCount(5))
            self.fail("Expected RetryError after 3 attempts")
        except RetryError as re:
            self.assertFalse(re.last_attempt.has_exception)
            self.assertEqual(3, re.last_attempt.attempt_number)
            self.assertTrue(re.last_attempt.value is None)
            print(re)

    def test_with_stop_on_exception(self):
        try:
            _retryable_test_with_stop(NoIOErrorAfterCount(5))
            self.fail("Expected IOError")
        except IOError as re:
            self.assertTrue(isinstance(re, IOError))
            print(re)

    def test_retry_if_exception_of_type(self):
        self.assertTrue(_retryable_test_with_exception_type_io(NoIOErrorAfterCount(5)))

        try:
            _retryable_test_with_exception_type_io(NoNameErrorAfterCount(5))
            self.fail("Expected NameError")
        except NameError as n:
            self.assertTrue(isinstance(n, NameError))
            print(n)

        try:
            _retryable_test_with_exception_type_io_attempt_limit_wrap(
                NoIOErrorAfterCount(5)
            )
            self.fail("Expected RetryError")
        except RetryError as re:
            self.assertEqual(3, re.last_attempt.attempt_number)
            self.assertTrue(re.last_attempt.has_exception)
            self.assertTrue(re.last_attempt.value[0] is not None)
            self.assertTrue(isinstance(re.last_attempt.value[1], IOError))
            self.assertTrue(re.last_attempt.value[2] is not None)
            print(re)

        self.assertTrue(
            _retryable_test_with_exception_type_custom(NoCustomErrorAfterCount(5))
        )

        try:
            _retryable_test_with_exception_type_custom(NoNameErrorAfterCount(5))
            self.fail("Expected NameError")
        except NameError as n:
            self.assertTrue(isinstance(n, NameError))
            print(n)

        try:
            _retryable_test_with_exception_type_custom_attempt_limit_wrap(
                NoCustomErrorAfterCount(5)
            )
            self.fail("Expected RetryError")
        except RetryError as re:
            self.assertEqual(3, re.last_attempt.attempt_number)
            self.assertTrue(re.last_attempt.has_exception)
            self.assertTrue(re.last_attempt.value[0] is not None)
            self.assertTrue(isinstance(re.last_attempt.value[1], CustomError))
            self.assertTrue(re.last_attempt.value[2] is not None)
            print(re)

    def test_wrapped_exception(self):

        # base exception cases
        self.assertTrue(
            _retryable_test_with_exception_type_io_wrap(NoIOErrorAfterCount(5))
        )

        try:
            _retryable_test_with_exception_type_io_wrap(NoNameErrorAfterCount(5))
            self.fail("Expected RetryError")
        except RetryError as re:
            self.assertTrue(isinstance(re.last_attempt.value[1], NameError))
            print(re)

        try:
            _retryable_test_with_exception_type_io_attempt_limit_wrap(
                NoIOErrorAfterCount(5)
            )
            self.fail("Expected RetryError")
        except RetryError as re:
            self.assertEqual(3, re.last_attempt.attempt_number)
            self.assertTrue(re.last_attempt.has_exception)
            self.assertTrue(re.last_attempt.value[0] is not None)
            self.assertTrue(isinstance(re.last_attempt.value[1], IOError))
            self.assertTrue(re.last_attempt.value[2] is not None)
            print(re)

        # custom error cases
        self.assertTrue(
            _retryable_test_with_exception_type_custom_wrap(NoCustomErrorAfterCount(5))
        )

        try:
            _retryable_test_with_exception_type_custom_wrap(NoNameErrorAfterCount(5))
            self.fail("Expected RetryError")
        except RetryError as re:
            self.assertTrue(re.last_attempt.value[0] is not None)
            self.assertTrue(isinstance(re.last_attempt.value[1], NameError))
            self.assertTrue(re.last_attempt.value[2] is not None)
            print(re)

        try:
            _retryable_test_with_exception_type_custom_attempt_limit_wrap(
                NoCustomErrorAfterCount(5)
            )
            self.fail("Expected RetryError")
        except RetryError as re:
            self.assertEqual(3, re.last_attempt.attempt_number)
            self.assertTrue(re.last_attempt.has_exception)
            self.assertTrue(re.last_attempt.value[0] is not None)
            self.assertTrue(isinstance(re.last_attempt.value[1], CustomError))
            self.assertTrue(re.last_attempt.value[2] is not None)

            self.assertTrue(
                "This is a Custom exception class" in str(re.last_attempt.value[1])
            )
            print(re)

    def test_defaults(self):
        self.assertTrue(_retryable_default(NoNameErrorAfterCount(5)))
        self.assertTrue(_retryable_default_f(NoNameErrorAfterCount(5)))
        self.assertTrue(_retryable_default(NoCustomErrorAfterCount(5)))
        self.assertTrue(_retryable_default_f(NoCustomErrorAfterCount(5)))


class TestBeforeAfterAttempts(unittest.TestCase):
    _attempt_number = 0

    def test_before_attempts(self):
        TestBeforeAfterAttempts._attempt_number = 0

        def _before(attempt_number):
            TestBeforeAfterAttempts._attempt_number = attempt_number

        @retry(wait_fixed=1000, stop_max_attempt_number=1, before_attempts=_before)
        def _test_before():
            pass

        _test_before()

        self.assertTrue(TestBeforeAfterAttempts._attempt_number == 1)

    def test_after_attempts(self):
        TestBeforeAfterAttempts._attempt_number = 0

        def _after(attempt_number):
            TestBeforeAfterAttempts._attempt_number = attempt_number

        @retry(wait_fixed=100, stop_max_attempt_number=3, after_attempts=_after)
        def _test_after():
            if TestBeforeAfterAttempts._attempt_number < 2:
                raise Exception("testing after_attempts handler")
            else:
                pass

        _test_after()

        self.assertTrue(TestBeforeAfterAttempts._attempt_number == 2)


class LoadTest(unittest.TestCase):
    total_calls = 0
    foo = "bar"  # Static value to reduce variance

    @retry(
        retry_on_result=lambda result: result is None,
        stop_max_attempt_number=30000,  # For this test, never raise an exception
        wait_fixed=0
    )
    def fn_to_test(self):
        LoadTest.total_calls += 1
        # Simulate sometimes returning None (triggering retry)
        if random.random() < 0.4:
            return LoadTest.foo
        else:
            return None

    def benchmark(self, duration_seconds=2):
        # Reset counter
        LoadTest.total_calls = 0

        start_time = time.time()
        end_time = start_time + duration_seconds

        while time.time() < end_time:
            _ = self.fn_to_test()

        actual_duration = time.time() - start_time

        # Calculate metrics
        calls_per_second = LoadTest.total_calls / actual_duration
        return calls_per_second

    def test_load(self):
        """
        In 1.3.5, there was a bug where calls wrapped with retry would take longer and longer to complete.
        This test checks that wrapping a function with retry doesn't affect its performance over several calls.
        This test takes ~24 seconds to run.
        """
        calls_per_second_initial = self.benchmark(2)
        # Run the benchmark a few more times. This triggers the performance bug in 1.3.5.
        for i in range(10):
            _ = self.benchmark(2)
        calls_per_second_final = self.benchmark(2)
        # Ensure that the later calls are within +/-20% the speed of the initial calls
        self.assertTrue(
            calls_per_second_initial * 0.8 <= calls_per_second_final <= calls_per_second_initial * 1.2,
            {
                "calls_per_second_initial": calls_per_second_initial,
                "calls_per_second_final": calls_per_second_final,
                "msg": "calls_per_second_final was not within +/-20% of calls_per_second_initial"
            }
        )


class TestLogger(unittest.TestCase):
    def setUp(self):
        # Set up a function with a dummy logger
        self.logger = logging.getLogger("test_retrying")
        self.test_handler = self.TestHandler()
        self.logger.addHandler(self.test_handler)
        @retry(stop_max_attempt_number=1, retry_on_result=lambda r: r is None, logger=self.logger)
        def foo_with_logger():
            return None
        self.foo_with_logger = foo_with_logger

    class TestHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def handle(self, record):
            self.records.append(record)

    @retry(stop_max_attempt_number=1, retry_on_result=lambda r: r is None)
    def foo_no_logger(self):
        return None

    def test_logger_None(self):
        # Assert not raises (anything except RetryError)
        try:
            self.foo_no_logger()
        except RetryError:
            pass

    def test_logger_custom(self):
        try:
            self.foo_with_logger()
        except RetryError:
            pass
        self.assertEqual(len(self.test_handler.records), 1)

    def test_logger_true(self):
        @retry(stop_max_attempt_number=1, retry_on_result=lambda r: r is None, logger=True)
        def foo_true():
            return None

        # Assert not raises (anything except RetryError)
        try:
            foo_true()
        except RetryError:
            pass


if __name__ == "__main__":
    unittest.main()
