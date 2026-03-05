# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_on_wink = fields.Boolean(
        string='Available on Wink',
        help="Check this box to make this service available on the Wink portal."
    )
    is_bundle = fields.Boolean(
        string='Is a Bundle Template?',
        help="Check this if this product template is acting as a parent wrapper for a bundle package."
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
    nature_id = fields.Many2one(
        'kuec.service.nature',
        string='Service Nature'
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
    wink_subscription_group_id = fields.Many2one(
        'wink.subscription.group',
        string='Subscription Group',
        ondelete='set null',
        help='Links this retainer service to its upgrade/downgrade/cancellation policy group. '
             'Defines standard monthly prices per plan tier for proration calculations.',
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

    # Portal tags vs ribbon: separate single ribbon tag for clearer UX
    wink_ribbon_tag_id = fields.Many2one(
        'product.tag',
        string='Ribbon (Portal)',
        domain=[('is_ribbon', '=', True)],
        help='Single ribbon tag shown as the diagonal ribbon on the Wink portal card and detail page.',
    )

    @api.onchange('commercial_structure')
    def _onchange_commercial_structure(self):
        if self.commercial_structure == 'bundled':
            self.available_on_wink = False

    @api.onchange('delivery_model')
    def _onchange_delivery_model(self):
        if self.delivery_model == 'retainer':
            self.recurring_invoice = True

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
                tmpl_field = 'product_tmpl_id' if 'product_tmpl_id' in Pricing._fields else ('product_template_id' if 'product_template_id' in Pricing._fields else None)
                if tmpl_field:
                    lines = Pricing.search([(tmpl_field, '=', product.id)])
                    if lines:
                        return _sort_lines(lines)
                variant_ids = product.product_variant_ids.ids or (
                    [product.product_variant_id.id] if product.product_variant_id else []
                )
                if 'product_id' in Pricing._fields:
                    var_domain = [('product_id', 'in', variant_ids)]
                elif 'product_variant_ids' in Pricing._fields:
                    var_domain = [('product_variant_ids', 'in', variant_ids)]
                else:
                    var_domain = []

                if variant_ids and var_domain:
                    lines = Pricing.search(var_domain)
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
        # Resolve currency: pricelist > company
        if pricelist_id:
            pricelist = self.env['product.pricelist'].sudo().browse(pricelist_id)
            currency = pricelist.currency_id if pricelist.exists() else self.env.company.currency_id
        else:
            currency = self.env.company.currency_id
        currency_symbol = currency.symbol or currency.name or 'AED'
        currency_name = currency.name or 'AED'
        # Resolve recurrence and price from each line (product.pricing or similar)
        plans_raw = []
        for line in lines:
            recurrence = getattr(line, 'recurrence_id', None) or getattr(line, 'recurring_plan_id', None) or getattr(line, 'plan_id', None)
            if not recurrence:
                continue
            price = getattr(line, 'price', None) or getattr(line, 'recurring_price', None) or getattr(line, 'list_price', None) or 0
            months = self._recurrence_duration_months(recurrence)
            name = getattr(recurrence, 'name', None) or ('%s %s' % (getattr(recurrence, 'duration', 1), getattr(recurrence, 'unit', 'month')))
            
            variant_id = None
            variant_attribute_names = []
            if hasattr(line, 'product_variant_ids') and line.product_variant_ids and len(self.product_variant_ids) > 1:
                v = line.product_variant_ids[0]
                variant_id = v.id
                variant_attribute_names = v.product_template_attribute_value_ids.mapped('name')
                if self.commercial_structure != 'bundled':
                    variant_name = ", ".join(variant_attribute_names)
                    if variant_name:
                        name = f"{variant_name} ({name})"
            elif hasattr(line, 'product_id') and line.product_id and len(self.product_variant_ids) > 1:
                v = line.product_id
                variant_id = v.id
                variant_attribute_names = v.product_template_attribute_value_ids.mapped('name')
                if self.commercial_structure != 'bundled':
                    variant_name = ", ".join(variant_attribute_names)
                    if variant_name:
                        name = f"{variant_name} ({name})"
            plans_raw.append({
                'line': line,
                'pricing_id': line.id,
                'recurrence': recurrence,
                'recurrence_id': recurrence.id,
                'plan_name': name,
                'price': float(price),
                'months': months,
                'duration': getattr(recurrence, 'duration', 1),
                'unit': getattr(recurrence, 'unit', 'month'),
                'variant_id': variant_id,
                'variant_attribute_names': variant_attribute_names,
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
            # Derive period_label from billing_period (relativedelta) or plan name
            billing_period = getattr(recurrence, 'billing_period', None)
            if billing_period:
                years = getattr(billing_period, 'years', 0) or 0
                months = getattr(billing_period, 'months', 0) or 0
                if years >= 1:
                    period_label = 'per year' if years == 1 else 'per %d years' % years
                elif months >= 12:
                    period_label = 'per year'
                elif months == 3:
                    period_label = 'per quarter'
                elif months == 6:
                    period_label = 'per 6 months'
                elif months > 1:
                    period_label = 'per %d months' % months
                else:
                    period_label = 'per month'
            else:
                # Fallback: derive from plan name string
                plan_name_lower = name.lower()
                if 'year' in plan_name_lower or 'annual' in plan_name_lower:
                    period_label = 'per year'
                elif 'quarter' in plan_name_lower:
                    period_label = 'per quarter'
                elif 'semi' in plan_name_lower or '6 month' in plan_name_lower:
                    period_label = 'per 6 months'
                else:
                    period_label = 'per month'
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
                'variant_id': p.get('variant_id'),
                'pricing_id': p['line'].id,
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
                'currency_symbol': currency_symbol,
                'currency_name': currency_name,
                'variant_id': p.get('variant_id'),
                'variant_attribute_names': p.get('variant_attribute_names', []),
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
