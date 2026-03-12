# -*- coding: utf-8 -*-
# Extension point for sale.subscription.pricing (e.g. kuec_plan_features, kuec_is_most_popular).
# Reference plan is on sale.subscription.plan (sale_subscription_plan.py), not here.

from odoo import models


class SaleSubscriptionPricing(models.Model):
    _inherit = 'sale.subscription.pricing'
