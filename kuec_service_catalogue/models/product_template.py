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

    wink_recurrence_id = fields.Many2one(
        'sale.recurrence',
        string='Recurrence Plan',
        ondelete='set null',
        help="Recurrence plan applied to portal orders for retainer services.",
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
        """Return native Recurring Prices for portal plan selection (retainer).
        Uses sudo so portal users can see plans. Supports product.pricing (Time-based pricing)
        and sale.subscription.plan linked to product."""
        self.ensure_one()
        product = self.sudo()
        # 1) One2many pricing lines on product.template (Odoo 18: pricing_ids, etc.)
        for field_name in (
            'pricing_ids',
            'product_pricing_ids',
            'recurring_pricing_ids',
            'subscription_pricing_ids',
            'time_based_pricing_ids',
            'subscription_pricing_line_ids',
            'recurring_pricing_line_ids',
        ):
            if field_name in product._fields:
                lines = product[field_name]
                if lines:
                    key = lambda p: (getattr(p, 'sequence', 0), p.id)
                    return lines.sorted(key=key)
        # 2) product.pricing: search by product_tmpl_id or by product_id (variant)
        try:
            Pricing = self.env['product.pricing'].sudo()
            if 'product_tmpl_id' in Pricing._fields:
                lines = Pricing.search([('product_tmpl_id', '=', product.id)])
                if lines:
                    return lines.sorted(key=lambda p: (getattr(p, 'sequence', 0), p.id))
            if 'product_id' in Pricing._fields:
                variant_ids = product.product_variant_ids.ids or (product.product_variant_id and [product.product_variant_id.id] or [])
                if variant_ids:
                    lines = Pricing.search([('product_id', 'in', variant_ids)])
                    if lines:
                        return lines.sorted(key=lambda p: (getattr(p, 'sequence', 0), p.id))
        except (KeyError, AttributeError):
            pass
        # 3) sale.subscription.plan: product linked via Many2many or plan has product_tmpl_id
        try:
            Plan = self.env['sale.subscription.plan'].sudo()
            for field_name in ('plan_ids', 'subscription_plan_ids', 'recurring_plan_ids'):
                if field_name in product._fields and product[field_name]:
                    plans = product[field_name]
                    return plans.sorted(key=lambda p: (getattr(p, 'sequence', 0), p.id))
            if Plan._fields.get('product_tmpl_id'):
                plans = Plan.search([('product_tmpl_id', '=', product.id)])
                if plans:
                    return plans.sorted(key=lambda p: (getattr(p, 'sequence', 0), p.id))
        except (KeyError, AttributeError):
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
