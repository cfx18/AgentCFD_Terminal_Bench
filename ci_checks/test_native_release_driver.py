"""No-execution checks for the native release driver's observation and log parser."""
import unittest
from unittest.mock import patch

from ci_checks.qualify_deployed_release import effective_coefficients, observe
from agentcfd_bench.foam.default_coefficients import DEFAULTS
from agentcfd_bench.runtime import Pending


class DriverTests(unittest.TestCase):
    def block(self, values=None):
        return 'kEpsilonCoeffs\n{\n'+''.join(
            f'{k} {v};\n' for k,v in (values or DEFAULTS).items())+'}\n'

    def test_actual_and_equivalent_numbers(self):
        self.assertEqual(effective_coefficients(self.block(),DEFAULTS),DEFAULTS)
        values = {**DEFAULTS,'Cmu':'9e-2','sigmak':'1.000'}
        self.assertEqual(effective_coefficients(self.block(values),DEFAULTS)['Cmu'],'0.09')

    def test_missing_duplicate_and_unknown_blocks(self):
        for log in ('',self.block()*2,self.block({**DEFAULTS,'unknown':'1'})):
            with self.subTest(log=log), self.assertRaises(ValueError):
                effective_coefficients(log,DEFAULTS)

    def test_every_changed_coefficient_rejected(self):
        for key in DEFAULTS:
            with self.subTest(key=key), self.assertRaises(ValueError):
                effective_coefficients(self.block({**DEFAULTS,key:'9'}),DEFAULTS)

    def test_pending_observes_same_operation(self):
        outcomes = [Pending('existing operation'),Pending('existing operation'),{'exit':0}]
        def operation():
            value = outcomes.pop(0)
            if isinstance(value,Exception):
                raise value
            return value
        with patch('ci_checks.qualify_deployed_release.time.sleep') as sleep:
            self.assertEqual(observe(operation),{'exit':0})
            self.assertEqual(sleep.call_count,2)
        self.assertEqual(outcomes,[])

    def test_unregistered_failure_is_not_retried(self):
        with patch('ci_checks.qualify_deployed_release.time.sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError,'not a queue state'):
                observe(lambda:(_ for _ in ()).throw(RuntimeError('not a queue state')))
            sleep.assert_not_called()

    def test_observation_deadline_does_not_replace_operation(self):
        with patch('ci_checks.qualify_deployed_release.time.monotonic',side_effect=[0,601]), \
             patch('ci_checks.qualify_deployed_release.time.sleep') as sleep:
            with self.assertRaises(Pending):
                observe(lambda:(_ for _ in ()).throw(Pending('unresolved')))
            sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
