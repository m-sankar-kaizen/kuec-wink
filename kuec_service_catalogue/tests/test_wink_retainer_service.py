# -*- coding: utf-8 -*-
# RET-004: Unit tests for wink_retainer_change_service (classify_change only).
# Subscription group/plan models removed — proration and policy tests disabled.
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


class _MockPlan:
    """Minimal mock for plan objects in classify_change tests."""
    def __init__(self, id_, sequence):
        self.id = id_
        self.sequence = sequence


@tagged('post_install', '-at_install')
class TestWinkRetainerChangeService(TransactionCase):
    """Unit tests for classify_change (sequence-based upgrade/downgrade)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env['wink.retainer.change.service']

    def test_classify_change_upgrade(self):
        """Lower sequence -> higher sequence = upgrade."""
        bronze = _MockPlan(1, 10)
        silver = _MockPlan(2, 20)
        result = self.service.classify_change(bronze, silver)
        self.assertEqual(result, 'upgrade')

    def test_classify_change_downgrade(self):
        """Higher sequence -> lower sequence = downgrade."""
        bronze = _MockPlan(1, 10)
        silver = _MockPlan(2, 20)
        result = self.service.classify_change(silver, bronze)
        self.assertEqual(result, 'downgrade')

    def test_classify_change_same_plan(self):
        """Same plan id = None."""
        p = _MockPlan(1, 10)
        result = self.service.classify_change(p, p)
        self.assertIsNone(result)

    def test_classify_change_same_sequence(self):
        """Same sequence = None (no upgrade/downgrade)."""
        p1 = _MockPlan(1, 10)
        p2 = _MockPlan(2, 10)
        result = self.service.classify_change(p1, p2)
        self.assertIsNone(result)

    def test_classify_change_none_source(self):
        """None source returns None."""
        p = _MockPlan(2, 20)
        result = self.service.classify_change(None, p)
        self.assertIsNone(result)
