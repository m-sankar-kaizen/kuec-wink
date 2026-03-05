# -*- coding: utf-8 -*-
# RET-004: Unit tests for wink_retainer_change_service
from datetime import date, timedelta
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestWinkRetainerChangeService(TransactionCase):
    """Unit tests for classify_change, compute_proration, validate_policy."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env['wink.retainer.change.service']
        cls.Group = cls.env['wink.subscription.group']
        cls.Plan = cls.env['wink.subscription.plan']
        cls.Product = cls.env['product.template']
        cls.Partner = cls.env['res.partner']
        cls.Order = cls.env['sale.order']
        cls.Currency = cls.env['res.currency']

        cls.partner = cls.Partner.create({
            'name': 'Test Partner',
        })
        cls.currency = cls.env.company.currency_id

        cls.group = cls.Group.create({
            'name': 'Test Retainer Group',
            'allow_upgrade': True,
            'allow_downgrade': True,
            'allow_cancellation': True,
            'min_days_before_change': 0,
        })
        cls.plan_bronze = cls.Plan.create({
            'name': 'Bronze',
            'group_id': cls.group.id,
            'sequence': 10,
            'monthly_std_price': 100.0,
        })
        cls.plan_silver = cls.Plan.create({
            'name': 'Silver',
            'group_id': cls.group.id,
            'sequence': 20,
            'monthly_std_price': 200.0,
        })
        cls.plan_gold = cls.Plan.create({
            'name': 'Gold',
            'group_id': cls.group.id,
            'sequence': 30,
            'monthly_std_price': 300.0,
        })

        cls.product = cls.Product.create({
            'name': 'Test Retainer Service',
            'type': 'service',
            'sale_ok': True,
            'wink_subscription_group_id': cls.group.id,
        })

    def _create_order(self, plan=None, next_date=None, **kw):
        """Create a minimal sale order for testing."""
        vals = {
            'partner_id': self.partner.id,
            'wink_source_product_id': self.product.id,
            'wink_plan_id': plan and plan.id or self.plan_bronze.id,
            'wink_is_portal_request': True,
        }
        if next_date and 'next_invoice_date' in self.Order._fields:
            vals['next_invoice_date'] = next_date
        vals.update(kw)
        return self.Order.create(vals)

    def test_classify_change_upgrade(self):
        """Bronze (10) -> Silver (20) = upgrade."""
        result = self.service.classify_change(self.plan_bronze, self.plan_silver)
        self.assertEqual(result, 'upgrade')

    def test_classify_change_downgrade(self):
        """Silver (20) -> Bronze (10) = downgrade."""
        result = self.service.classify_change(self.plan_silver, self.plan_bronze)
        self.assertEqual(result, 'downgrade')

    def test_classify_change_same_plan(self):
        """Same plan = None."""
        result = self.service.classify_change(self.plan_bronze, self.plan_bronze)
        self.assertIsNone(result)

    def test_classify_change_same_sequence(self):
        """Same sequence = None (no upgrade/downgrade)."""
        plan_alt = self.Plan.create({
            'name': 'Bronze Alt',
            'group_id': self.group.id,
            'sequence': 10,
            'monthly_std_price': 150.0,
        })
        result = self.service.classify_change(self.plan_bronze, plan_alt)
        self.assertIsNone(result)

    def test_classify_change_none_source(self):
        """None source returns None."""
        result = self.service.classify_change(None, self.plan_silver)
        self.assertIsNone(result)

    def test_compute_proration_upgrade(self):
        """Upgrade: charge > credit, net_amount positive."""
        today = date.today()
        end_date = today + timedelta(days=15)
        order = self._create_order(plan=self.plan_bronze, next_date=end_date)
        if not getattr(order, 'next_invoice_date', None) and not getattr(order, 'next_date', None):
            with patch.object(type(self.service), '_get_end_date', return_value=end_date):
                result = self.service.compute_proration(order, self.plan_silver, 'immediate')
        else:
            result = self.service.compute_proration(order, self.plan_silver, 'immediate')

        self.assertIsNone(result['error'])
        self.assertEqual(result['remaining_days'], 15)
        self.assertEqual(result['current_monthly_std_price'], 100.0)
        self.assertEqual(result['target_monthly_std_price'], 200.0)
        # Credit: 100/30 * 15 = 50
        self.assertEqual(result['proration_credit'], 50.0)
        # Charge: 200/30 * 15 = 100
        self.assertEqual(result['proration_charge'], 100.0)
        self.assertEqual(result['net_amount'], 50.0)
        self.assertEqual(result['effective_date'], today)

    def test_compute_proration_downgrade(self):
        """Downgrade: charge < credit, net_amount negative."""
        today = date.today()
        end_date = today + timedelta(days=15)
        order = self._create_order(plan=self.plan_silver, next_date=end_date)
        has_end = bool(getattr(order, 'next_invoice_date', None) or getattr(order, 'next_date', None))
        if not has_end:
            with patch.object(type(self.service), '_get_end_date', return_value=end_date):
                result = self.service.compute_proration(order, self.plan_bronze, 'immediate')
        else:
            result = self.service.compute_proration(order, self.plan_bronze, 'immediate')

        self.assertIsNone(result['error'])
        self.assertEqual(result['remaining_days'], 15)
        self.assertEqual(result['current_monthly_std_price'], 200.0)
        self.assertEqual(result['target_monthly_std_price'], 100.0)
        self.assertEqual(result['proration_credit'], 100.0)
        self.assertEqual(result['proration_charge'], 50.0)
        self.assertEqual(result['net_amount'], -50.0)

    def test_compute_proration_no_end_date(self):
        """No next_date/next_invoice_date returns error."""
        order = self._create_order(plan=self.plan_bronze)
        # Order has no next_date/next_invoice_date set; service returns error
        result = self.service.compute_proration(order, self.plan_silver, 'immediate')
        self.assertIsNotNone(result['error'])
        self.assertIn('No active subscription period', result['error'])

    def test_validate_policy_blocks_downgrade_when_disallowed(self):
        """Policy allow_downgrade=False blocks downgrade."""
        self.group.allow_downgrade = False
        today = date.today()
        end_date = today + timedelta(days=30)
        order = self._create_order(plan=self.plan_silver, next_date=end_date)

        ok, msg = self.service.validate_policy(order, self.plan_bronze, 'downgrade')

        self.assertFalse(ok)
        self.assertIn('Downgrades are not allowed', msg)

    def test_validate_policy_blocks_upgrade_when_disallowed(self):
        """Policy allow_upgrade=False blocks upgrade."""
        self.group.allow_upgrade = False
        today = date.today()
        end_date = today + timedelta(days=30)
        order = self._create_order(plan=self.plan_bronze, next_date=end_date)

        ok, msg = self.service.validate_policy(order, self.plan_silver, 'upgrade')

        self.assertFalse(ok)
        self.assertIn('Upgrades are not allowed', msg)

    def test_validate_policy_blocks_when_cancellation_requested(self):
        """Plan change blocked when wink_cancellation_requested=True."""
        today = date.today()
        end_date = today + timedelta(days=30)
        order = self._create_order(plan=self.plan_bronze, next_date=end_date)
        order.wink_cancellation_requested = True

        ok, msg = self.service.validate_policy(order, self.plan_silver, 'upgrade')

        self.assertFalse(ok)
        self.assertIn('cancellation', msg.lower())
