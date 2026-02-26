# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_on_wink = fields.Boolean(
        string='Available on Wink',
        help="Check this box to make this service available on the Wink portal."
    )

    kuec_document_ids = fields.One2many(
        'kuec.service.document',
        'product_tmpl_id',
        string='Required Documents'
    )

    # Layer 2 Classification Fields
    department_ids = fields.Many2many(
        'kuec.department',
        string='Departments'
    )
    nature_ids = fields.Many2many(
        'kuec.service.nature',
        string='Service Natures'
    )
    delivery_model = fields.Selection(
        selection=[
            ('project', 'Project'),
            ('retainer', 'Retainer')
        ],
        string='Delivery Model'
    )
    # project_template_id from sale_project is used for project delivery (see product_template_views.xml)
    commercial_structure = fields.Selection(
        selection=[
            ('standalone', 'Standalone'),
            ('bundled', 'Bundled'),
            ('flexible', 'Flexible')
        ],
        string='Commercial Structure'
    )
    request_frequency = fields.Selection(
        selection=[
            ('one_time', 'One Time'),
            ('repeated', 'Repeated')
        ],
        string='Request Frequency',
        default='one_time'
    )

    # Bundle
    wink_bundle_id = fields.Many2one(
        'wink.bundle',
        string='Bundle Package',
        ondelete='set null',
        help="The bundle this product belongs to. Only for bundled services.",
    )
    # Odoo native subscription plans (quotation templates); used when product has no Recurring Prices
    wink_subscription_plan_ids = fields.Many2many(
        'sale.order.template',
        'product_template_sale_order_template_rel',
        'product_tmpl_id',
        'sale_order_template_id',
        string='Subscription Plans (fallback)',
        help='Used for portal plan selection only if Recurring Prices tab is empty. Prefer Recurring Prices (Odoo native).',
    )

    def _wink_recurring_plan_lines(self):
        """Return native Recurring Prices (Recurring Plan + Recurring Price) for portal plan selection.
        Supports product.pricing (with plan_id -> sale.subscription.plan) and product links to sale.subscription.plan."""
        self.ensure_one()
        # 1) One2many pricing lines on product (product.pricing or similar with plan_id)
        for field_name in ('product_pricing_ids', 'recurring_pricing_ids', 'subscription_pricing_ids', 'pricing_ids'):
            if field_name in self._fields:
                lines = self[field_name]
                if lines:
                    key = lambda p: (getattr(p, 'sequence', 0), p.id)
                    return lines.sorted(key=key)
                return lines
        try:
            Pricing = self.env['product.pricing']
            if 'product_tmpl_id' in Pricing._fields:
                lines = Pricing.search([('product_tmpl_id', '=', self.id)])
                if lines:
                    key = lambda p: (getattr(p, 'sequence', 0), p.id)
                    return lines.sorted(key=key)
                return lines
        except KeyError:
            pass
        # 2) sale.subscription.plan (plan_id): product linked to plans (e.g. plan_ids, subscription_plan_ids)
        try:
            Plan = self.env['sale.subscription.plan']
            for field_name in ('plan_ids', 'subscription_plan_ids', 'recurring_plan_ids'):
                if field_name in self._fields:
                    plans = self[field_name]
                    if plans:
                        key = lambda p: (getattr(p, 'sequence', 0), p.id)
                        return plans.sorted(key=key)
                    return plans
            # Plans with product_tmpl_id (e.g. plan line model linking plan to product)
            if Plan._fields.get('product_tmpl_id'):
                plans = Plan.search([('product_tmpl_id', '=', self.id)])
                if plans:
                    return plans.sorted(key=lambda p: (getattr(p, 'sequence', 0), p.id))
        except KeyError:
            pass
        return []

    reminder_days_before = fields.Integer(
        string='Reminder Days Before Expiry',
        default=0,
        help='Odoo will use the global Wink Settings if this is 0.'
    )

    # Layer 4 Website / Portal Extensions
    wink_description = fields.Html(
        string='Service Overview (Portal)',
        translate=True
    )
    wink_faq_ids = fields.One2many(
        'kuec.service.faq',
        'product_tmpl_id',
        string='Service FAQs'
    )
    price_visibility = fields.Selection([
        ('visible', 'Visible'),
        ('hidden', 'Hidden (Requires Coordinator)')
    ], string='Price Visibility on Portal', default='visible')
    price_hidden_label = fields.Char(
        string='Hidden Price Label',
        default='Contact us for pricing',
        translate=True
    )
    wink_payment_term_id = fields.Many2one(
        'account.payment.term',
        string='WINK Payment Term',
        domain=[('active', '=', True)],
        help='Specific payment terms to apply when this service is requested from the portal.'
    )
    requires_employee_selection = fields.Boolean(
        string='Requires Employee Selection',
        default=False,
        help="When enabled, the customer must select one or more employees from their directory when submitting a service request for this service."
    )

    @api.onchange('delivery_model')
    def _onchange_delivery_model_subscription(self):
        """Native Odoo 18 Subscription Configuration."""
        for template in self:
            if template.delivery_model == 'retainer':
                if 'recurring_invoice' in template._fields:
                    template.recurring_invoice = True
            elif template.delivery_model == 'project':
                if 'recurring_invoice' in template._fields:
                    template.recurring_invoice = False
