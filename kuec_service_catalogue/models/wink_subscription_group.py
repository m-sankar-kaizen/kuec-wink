# -*- coding: utf-8 -*-
# RET-001, RET-002
from odoo import models, fields, api, exceptions, _
from datetime import date


class WinkSubscriptionGroup(models.Model):
    """Groups subscription plans (e.g. Bronze/Silver/Gold) for a retainer service,
    defines per-plan standard monthly prices and upgrade/downgrade/cancellation policy.

    Policy rule (Story 1.12):
    - Proration is always calculated using the STANDARD MONTHLY PRICE (this field),
      regardless of whether the customer is on an annual or discounted plan.
    - Remaining value = (monthly_std_price / 30) × remaining_days
    - On upgrade: credit is applied toward the new plan.
    - On downgrade: difference may be credited to wallet or next billing cycle.
    - On cancellation: remaining value is refundable based on monthly rate.
    - Annual discount is FORFEITED when changing or cancelling before end date.
    """
    _name = 'wink.subscription.group'
    _description = 'WINK Subscription Group'
    _order = 'name'

    name = fields.Char(string='Group Name', required=True,
                       help='e.g. "HR Retainer Plans", "Legal Advisory Plans"')
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    # Policy settings
    allow_upgrade = fields.Boolean(
        string='Allow Upgrade', default=True,
        help='Customers may upgrade to a higher plan via the portal.')
    allow_downgrade = fields.Boolean(
        string='Allow Downgrade', default=True,
        help='Customers may downgrade to a lower plan via the portal.')
    allow_cancellation = fields.Boolean(
        string='Allow Cancellation', default=True,
        help='Customers may request cancellation via the portal.')
    downgrade_credit_policy = fields.Selection([
        ('wallet', 'Credit to Wallet'),
        ('next_cycle', 'Adjust in Next Billing Cycle'),
        ('no_refund', 'No Refund on Downgrade'),
    ], string='Downgrade Credit Policy', default='next_cycle',
        help='What happens with the remaining credit when a customer downgrades.')
    cancellation_credit_policy = fields.Selection([
        ('refund', 'Refund Remaining Value'),
        ('wallet', 'Credit to Wallet'),
        ('no_refund', 'No Refund on Cancellation'),
    ], string='Cancellation Credit Policy', default='refund',
        help='What happens with the remaining value when a customer cancels.')
    min_days_before_change = fields.Integer(
        string='Minimum Days Before Plan Change', default=0,
        help='Minimum number of days before the subscription end date that a change is allowed. '
             '0 = changes allowed anytime.')
    # RET-002: Approval flags for coordinator control
    upgrade_requires_approval = fields.Boolean(
        string='Upgrade Requires Approval', default=False,
        help='If checked, upgrade creates draft quote for coordinator approval.')
    downgrade_requires_approval = fields.Boolean(
        string='Downgrade Requires Approval', default=True,
        help='If checked, downgrade creates draft quote for coordinator approval.')
    cancellation_requires_approval = fields.Boolean(
        string='Cancellation Requires Approval', default=True,
        help='If checked, cancellation request awaits coordinator processing.')
    min_days_before_cancellation = fields.Integer(
        string='Minimum Days Before Cancellation', default=0,
        help='Override for cancellation only. 0 = use min_days_before_change.')
    effective_date_policy = fields.Selection([
        ('immediate', 'Immediate'),
        ('next_cycle', 'Next Billing Cycle'),
    ], string='Effective Date Policy', default='immediate',
        help='When does the plan change take effect.')

    plan_ids = fields.One2many(
        'wink.subscription.plan', 'group_id',
        string='Plans',
        help='Define each plan (Bronze, Silver, Gold) with its monthly standard price.')
    plan_count = fields.Integer(compute='_compute_plan_count', store=True)

    product_ids = fields.One2many(
        'product.template', 'wink_subscription_group_id',
        string='Services using this group')

    @api.depends('plan_ids')
    def _compute_plan_count(self):
        for rec in self:
            rec.plan_count = len(rec.plan_ids)


class WinkSubscriptionPlan(models.Model):
    """A named plan tier within a subscription group.
    Stores the standard monthly price used for proration calculations,
    independent of any annual discounts set in product.pricing.
    RET-001: Optional explicit link to recurring pricing record.
    """
    _name = 'wink.subscription.plan'
    _description = 'WINK Subscription Plan'
    _order = 'sequence, id'

    # RET-001: Explicit link to pricing (product.pricing or sale.subscription.pricing)
    # Stored as model,id to support both; resolved at runtime.
    pricing_model = fields.Char(
        string='Pricing Model', copy=False,
        help='Model name of linked pricing record (e.g. product.pricing).')
    pricing_id = fields.Integer(
        string='Pricing ID', copy=False,
        help='ID of the pricing record. Resolved with pricing_model.')

    group_id = fields.Many2one(
        'wink.subscription.group', string='Subscription Group',
        required=True, ondelete='cascade')
    name = fields.Char(string='Plan Name', required=True,
                       help='e.g. Bronze, Silver, Gold, Basic, Premium')
    sequence = fields.Integer(string='Sequence', default=10,
                              help='Lower = lower tier (used to determine upgrade vs downgrade).')
    active = fields.Boolean(default=True)

    # Fallback when no Odoo Recurring Price linked; primary source is product.pricing (per-service)
    monthly_std_price = fields.Float(
        string='Standard Monthly Price (fallback)',
        required=True, digits=(10, 2),
        help='Fallback for proration when no Odoo Recurring Price is linked to this plan. '
             'When each service has Recurring Prices (product.pricing), proration uses the actual '
             'price per service (normalized to monthly). Use this field when services share a group '
             'but have no pricing link, or for backward compatibility.')

    # Link to the Odoo native recurrence/pricing record for this plan
    # (so the system knows which portal plan card maps to this policy plan)
    recurrence_name_hint = fields.Char(
        string='Recurrence Name Hint',
        help='Optional: the recurrence name (e.g. "Monthly", "Annual") this plan corresponds to '
             'in the product Recurring Prices tab. Used for display only.')

    @api.constrains('monthly_std_price')
    def _check_price(self):
        for rec in self:
            if rec.monthly_std_price < 0:
                raise exceptions.ValidationError(
                    _('Standard monthly price cannot be negative for plan "%s".') % rec.name)

    def _compute_remaining_credit(self, subscription_start_date, subscription_end_date):
        """Compute the prorated remaining credit for this plan using standard monthly price.

        Formula (Story 1.12):
            remaining_value = (monthly_std_price / 30) * remaining_days

        Args:
            subscription_start_date: date — when the current subscription period started
            subscription_end_date: date — when the current subscription period ends

        Returns:
            dict with keys:
                remaining_days (int)
                daily_rate (float)
                remaining_value (float)
                monthly_std_price (float)
                note (str) — human-readable explanation
        """
        self.ensure_one()
        today = date.today()
        if subscription_end_date and subscription_end_date > today:
            remaining_days = (subscription_end_date - today).days
        else:
            remaining_days = 0

        daily_rate = self.monthly_std_price / 30.0
        remaining_value = round(daily_rate * remaining_days, 2)

        return {
            'remaining_days': remaining_days,
            'daily_rate': round(daily_rate, 4),
            'remaining_value': remaining_value,
            'monthly_std_price': self.monthly_std_price,
            'note': (
                f'Remaining value = ({self.monthly_std_price:,.2f} ÷ 30) × {remaining_days} days '
                f'= {remaining_value:,.2f} '
                f'(calculated at standard monthly rate, annual discount forfeited)'
            ),
        }
