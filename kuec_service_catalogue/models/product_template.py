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
        Uses sudo so portal users can see plans. Discovers the Recurring Prices One2many
        by field name and by dynamic detection (any One2many whose comodel has plan + price)."""
        self.ensure_one()
        product = self.sudo()

        def _sort_lines(lines):
            return lines.sorted(key=lambda p: (getattr(p, 'sequence', 0), p.id))

        def _is_pricing_comodel(model_name):
            """True if this model looks like recurring pricing (has plan/recurrence + price)."""
            try:
                M = self.env[model_name]
                plan = any(
                    f in M._fields for f in ('recurrence_id', 'recurring_plan_id', 'plan_id')
                )
                price = any(
                    f in M._fields for f in ('price', 'recurring_price', 'list_price')
                )
                return plan and price
            except KeyError:
                return False

        # 1) Explicit One2many field names (Odoo 18 / enterprise naming)
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
                    return _sort_lines(lines)

        # 2) Dynamic: any One2many on product.template whose comodel is recurring pricing
        for fname, field in product._fields.items():
            if field.type != 'one2many' or fname.startswith('kuec_') or fname.startswith('wink_'):
                continue
            try:
                comodel = field.comodel_name
                if not _is_pricing_comodel(comodel):
                    continue
                lines = product[fname]
                if lines:
                    return _sort_lines(lines)
            except (KeyError, AttributeError):
                continue

        # 3) Search by product_tmpl_id / product_id for known pricing model names
        for model_name in ('product.pricing', 'sale.subscription.pricing', 'product.recurring.pricing'):
            if not _is_pricing_comodel(model_name):
                continue
            try:
                Pricing = self.env[model_name].sudo()
                if 'product_tmpl_id' in Pricing._fields:
                    lines = Pricing.search([('product_tmpl_id', '=', product.id)])
                    if lines:
                        return _sort_lines(lines)
                if 'product_id' in Pricing._fields:
                    variant_ids = product.product_variant_ids.ids or (
                        [product.product_variant_id.id] if product.product_variant_id else []
                    )
                    if variant_ids:
                        lines = Pricing.search([('product_id', 'in', variant_ids)])
                        if lines:
                            return _sort_lines(lines)
            except KeyError:
                continue

        # 4) sale.subscription.plan: product linked via Many2many or plan has product_tmpl_id
        try:
            Plan = self.env['sale.subscription.plan'].sudo()
            for field_name in ('plan_ids', 'subscription_plan_ids', 'recurring_plan_ids'):
                if field_name in product._fields and product[field_name]:
                    return _sort_lines(product[field_name])
            if Plan._fields.get('product_tmpl_id'):
                plans = Plan.search([('product_tmpl_id', '=', product.id)])
                if plans:
                    return _sort_lines(plans)
        except (KeyError, AttributeError):
            pass
        return []

    def _recurrence_duration_months(self, recurrence):
        """Return duration in months for a recurrence record (sale.temporal.recurrence or similar)."""
        if not recurrence:
            return 1
        duration = getattr(recurrence, 'duration', 1) or 1
        unit = (getattr(recurrence, 'unit', 'month') or 'month').lower()
        if unit == 'year':
            return duration * 12
        if unit == 'month':
            return duration
        if unit == 'week':
            return round(duration * 12 / 52.0, 2)
        return duration

    def _wink_subscription_plans_dicts(self, pricelist_id=False):
        """Build subscription plan dicts for portal: plan_name, price, period_label, monthly_equivalent,
        savings_pct, show_savings, is_most_popular, features, recurrence_id, recurrence_id_str.
        Uses Monthly as baseline for savings; if no Monthly, use shortest period. pricelist_id=False for public."""
        self.ensure_one()
        lines = self.sudo()._wink_recurring_plan_lines()
        if not lines:
            return []
        # Resolve recurrence and price from each line (product.pricing or similar)
        plans_raw = []
        for line in lines:
            recurrence = getattr(line, 'recurrence_id', None) or getattr(line, 'recurring_plan_id', None) or getattr(line, 'plan_id', None)
            if not recurrence:
                continue
            price = getattr(line, 'price', None) or getattr(line, 'recurring_price', None) or getattr(line, 'list_price', None) or 0
            months = self._recurrence_duration_months(recurrence)
            name = getattr(recurrence, 'name', None) or ('%s %s' % (getattr(recurrence, 'duration', 1), getattr(recurrence, 'unit', 'month')))
            plans_raw.append({
                'line': line,
                'recurrence': recurrence,
                'recurrence_id': recurrence.id,
                'plan_name': name,
                'price': float(price),
                'months': months,
                'duration': getattr(recurrence, 'duration', 1),
                'unit': getattr(recurrence, 'unit', 'month'),
            })
        if not plans_raw:
            return []
        # Sort by duration ascending (Monthly first)
        plans_raw.sort(key=lambda p: (p['months'], p['recurrence_id']))
        # Period label and monthly equivalent
        unit_labels = {'month': 'month', 'year': 'year', 'week': 'weeks'}
        baseline_price_per_month = plans_raw[0]['price'] / plans_raw[0]['months'] if plans_raw[0]['months'] else plans_raw[0]['price']
        result = []
        for p in plans_raw:
            months = p['months']
            price = p['price']
            monthly_equivalent = round(price / months, 2) if months else price
            duration, unit = p['duration'], (p.get('unit') or 'month')
            if unit == 'month':
                period_label = 'per %s month' % duration if duration != 1 else 'per month'
            elif unit == 'year':
                period_label = 'per year'
            else:
                period_label = 'per %s %s' % (duration, unit_labels.get(unit, unit))
            # Savings vs baseline (shortest plan)
            savings_pct = 0
            if months > plans_raw[0]['months'] and baseline_price_per_month > 0:
                pct = (1 - (monthly_equivalent / baseline_price_per_month)) * 100
                savings_pct = max(0, round(pct))
            show_savings = savings_pct >= 1
            # Features and most popular from product.pricing
            line = p['line']
            features = []
            if getattr(line, 'kuec_plan_features', None):
                features = [s.strip() for s in (line.kuec_plan_features or '').splitlines() if s.strip()][:6]
            is_most_popular = bool(getattr(line, 'kuec_is_most_popular', False))
            result.append({
                'recurrence_id': p['recurrence_id'],
                'recurrence_id_str': str(p['recurrence_id']),
                'plan_name': p['plan_name'],
                'price': price,
                'period_label': period_label,
                'monthly_equivalent': monthly_equivalent,
                'savings_pct': savings_pct,
                'show_savings': show_savings,
                'is_most_popular': is_most_popular,
                'features': features,
            })
        return result

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
