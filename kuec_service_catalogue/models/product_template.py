# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_on_wink = fields.Boolean(
        string='Available on Wink',
        help="Check this box to make this service available on the Wink portal."
    )
    wink_is_bundle = fields.Boolean(
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

    wink_terms_html = fields.Html(
        string='Terms & Conditions',
        help='Product-specific terms and conditions shown to customers during portal request submission. '
             'If left empty the global company Terms & Conditions will be used.',
    )

    @api.onchange('wink_is_bundle')
    def _onchange_wink_is_bundle(self):
        if self.wink_is_bundle:
            self.delivery_model = 'retainer'
            self.recurring_invoice = True
            self.commercial_structure = 'bundled'
            self.available_on_wink = True
            self.request_frequency = 'repeated'

    @api.constrains('wink_is_bundle')
    def _check_bundle_delivery_model(self):
        """Bundles must have delivery_model=retainer and recurring_invoice=True."""
        for rec in self:
            if rec.wink_is_bundle:
                if rec.delivery_model != 'retainer':
                    raise ValidationError(
                        _('Bundle products must use Delivery Model "Retainer".')
                    )
                if not getattr(rec, 'recurring_invoice', True):
                    raise ValidationError(
                        _('Bundle products must have Subscriptions (recurring invoice) enabled.')
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('wink_is_bundle'):
                vals['delivery_model'] = 'retainer'
                vals['recurring_invoice'] = True
                vals.setdefault('request_frequency', 'repeated')
        templates = super().create(vals_list)
        for tmpl in templates:
            if tmpl.wink_is_bundle and not tmpl.wink_bundle_id:
                bundle = self.env['wink.bundle'].create({
                    'name': tmpl.name,
                    'company_id': tmpl.company_id.id or self.env.company.id,
                    'product_tmpl_id': tmpl.id,
                })
                tmpl.wink_bundle_id = bundle.id
        return templates

    def write(self, vals):
        """Enforce delivery_model=retainer and recurring_invoice when wink_is_bundle is set.
        Auto-create wink.bundle when wink_is_bundle is set to True and no bundle exists yet."""
        if vals.get('wink_is_bundle'):
            vals['delivery_model'] = 'retainer'
            vals['recurring_invoice'] = True
            if 'request_frequency' not in vals:
                vals['request_frequency'] = 'repeated'
        result = super().write(vals)
        if vals.get('wink_is_bundle'):
            for rec in self:
                if not rec.wink_bundle_id:
                    bundle = self.env['wink.bundle'].create({
                        'name': rec.name,
                        'company_id': rec.company_id.id or self.env.company.id,
                        'product_tmpl_id': rec.id,
                    })
                    rec.wink_bundle_id = bundle.id
                elif not rec.wink_bundle_id.product_tmpl_id:
                    rec.wink_bundle_id.product_tmpl_id = rec.id
        # Sync bundle name when the service template is renamed
        if 'name' in vals:
            for rec in self:
                if (rec.wink_is_bundle
                        and rec.wink_bundle_id
                        and rec.wink_bundle_id.product_tmpl_id.id == rec.id):
                    rec.wink_bundle_id.sudo().write({'name': vals['name']})
        return result

    def action_view_linked_bundle(self):
        """Open the linked wink.bundle form for this bundle template product."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bundle Package'),
            'res_model': 'wink.bundle',
            'res_id': self.wink_bundle_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.onchange('commercial_structure')
    def _onchange_commercial_structure(self):
        if self.commercial_structure == 'bundled' and not self.wink_is_bundle:
            # Sub-services belong inside a bundle tier only; portal controllers
            # exclude them from standalone catalogue/request flows.
            self.delivery_model = 'retainer'
            self.recurring_invoice = True

    @api.onchange('delivery_model')
    def _onchange_delivery_model(self):
        """Native Odoo 18 Subscription Configuration based on delivery model selection."""
        if self.delivery_model == 'retainer':
            self.recurring_invoice = True
        elif self.delivery_model == 'project':
            self.recurring_invoice = False

    def _wink_recurring_plan_lines(self, allow_plan_fallback=True):
        """Return recurring pricing rows for portal plan selection.

        When ``allow_plan_fallback`` is False, only actual Recurring Prices rows are
        returned. Bare sale.subscription.plan links are ignored so standalone retainer
        requests cannot proceed without a configured pricing row.
        """
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

        # 4) Fallback to bare plans only where legacy bundle flows still rely on it.
        if allow_plan_fallback:
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
        """Return duration in months for a recurrence record (sale.temporal.recurrence,
        sale.subscription.plan, or similar)."""
        if not recurrence:
            return 1
        # sale.subscription.plan uses billing_period_value / billing_period_unit
        duration = getattr(recurrence, 'duration', None) or getattr(recurrence, 'billing_period_value', 1) or 1
        unit = (getattr(recurrence, 'unit', None) or getattr(recurrence, 'billing_period_unit', 'month') or 'month').lower()
        if unit == 'year':
            return duration * 12
        if unit == 'month':
            return duration
        if unit == 'week':
            return round(duration * 12 / 52.0, 2)
        return duration

    def _wink_subscription_plans_dicts(self, pricelist_id=False, allow_plan_fallback=True):
        """Build subscription plan dicts for portal: plan_name, price, period_label, monthly_equivalent,
        savings_pct, show_savings, is_most_popular, features, recurrence_id, recurrence_id_str.
        Uses Monthly as baseline for savings; if no Monthly, use shortest period. pricelist_id=False for public."""
        self.ensure_one()
        lines = self.sudo()._wink_recurring_plan_lines(allow_plan_fallback=allow_plan_fallback)
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
            is_bundle_product = self.commercial_structure == 'bundled' or getattr(self, 'wink_is_bundle', False)
            if hasattr(line, 'product_variant_ids') and line.product_variant_ids and len(self.product_variant_ids) > 1:
                v = line.product_variant_ids[0]
                variant_id = v.id
                variant_attribute_names = v.product_template_attribute_value_ids.mapped('name')
                if not is_bundle_product:
                    variant_name = ", ".join(variant_attribute_names)
                    if variant_name:
                        name = f"{variant_name} ({name})"
            elif hasattr(line, 'product_id') and line.product_id and len(self.product_variant_ids) > 1:
                v = line.product_id
                variant_id = v.id
                variant_attribute_names = v.product_template_attribute_value_ids.mapped('name')
                if not is_bundle_product:
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
        # Build baseline per variant: for bundles with multiple tiers, each tier needs its own
        # reference (monthly) to compute savings. Key by (variant_id, variant_attribute_names).
        def _variant_key(p):
            vid = p.get('variant_id')
            if vid:
                return ('id', vid)
            attrs = tuple(sorted((a or '').lower() for a in p.get('variant_attribute_names', [])))
            return ('attrs', attrs) if attrs else ('default', 0)

        baseline_by_variant = {}
        reference_plan = next((p for p in plans_raw if getattr(p['recurrence'], 'kuec_is_reference_plan', False)), None)
        if reference_plan and reference_plan['months'] > 0:
            ref_key = _variant_key(reference_plan)
            baseline_by_variant[ref_key] = reference_plan['price'] / reference_plan['months']
        # Fallback: use shortest-period plan per variant as baseline
        for p in plans_raw:
            k = _variant_key(p)
            if k not in baseline_by_variant and p['months'] > 0:
                baseline_by_variant[k] = p['price'] / p['months']
        # Global fallback when no per-variant baseline
        default_baseline = (
            reference_plan['price'] / reference_plan['months'] if reference_plan and reference_plan['months']
            else plans_raw[0]['price'] / plans_raw[0]['months'] if plans_raw[0]['months'] else plans_raw[0]['price']
        )
        result = []
        for p in plans_raw:
            months = p['months']
            price = p['price']
            monthly_equivalent = round(price / months, 2) if months else price
            # Derive period_label from billing_period (relativedelta) or plan name
            # Use p['recurrence'] (not the stale loop variable) so each plan uses its own recurrence
            plan_recurrence = p['recurrence']
            billing_period = getattr(plan_recurrence, 'billing_period', None)
            if billing_period:
                bp_years = getattr(billing_period, 'years', 0) or 0
                bp_months = getattr(billing_period, 'months', 0) or 0
                if bp_years >= 1:
                    period_label = 'per year' if bp_years == 1 else 'per %d years' % bp_years
                elif bp_months >= 12:
                    period_label = 'per year'
                elif bp_months == 3:
                    period_label = 'per quarter'
                elif bp_months == 6:
                    period_label = 'per 6 months'
                elif bp_months > 1:
                    period_label = 'per %d months' % bp_months
                else:
                    period_label = 'per month'
            else:
                # Fallback: derive from plan name string
                plan_name_lower = p['plan_name'].lower()
                if 'year' in plan_name_lower or 'annual' in plan_name_lower:
                    period_label = 'per year'
                elif 'quarter' in plan_name_lower:
                    period_label = 'per quarter'
                elif 'semi' in plan_name_lower or '6 month' in plan_name_lower:
                    period_label = 'per 6 months'
                else:
                    period_label = 'per month'
            # Savings vs baseline (per-variant: each tier compares to its own monthly)
            line = p['line']
            is_reference_plan = bool(getattr(p['recurrence'], 'kuec_is_reference_plan', False))
            savings_pct = 0
            if not is_reference_plan:
                baseline_price_per_month = baseline_by_variant.get(_variant_key(p)) or default_baseline
                if baseline_price_per_month > 0:
                    pct = (1 - (monthly_equivalent / baseline_price_per_month)) * 100
                    savings_pct = max(0, round(pct))
            show_savings = savings_pct >= 1
            # Reference (pre-discount) price for crossed-out display: baseline_monthly × period_months
            # e.g. monthly=6000, annual=60000 → reference = 6000 × 12 = 72000 (not 60000/0.83)
            reference_price = price
            if show_savings and months and months > 0:
                _baseline = baseline_by_variant.get(_variant_key(p)) or default_baseline
                if _baseline > 0:
                    reference_price = round(_baseline * months, 2)
            # Features and most popular from pricing line
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
                'reference_price': reference_price,
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
    requires_government_charges = fields.Boolean(
        string='Requires Government Charges',
        default=False,
        help="When enabled, activating this service inside a bundle will flag the activation line "
             "for government charges. The coordinator must update the unit price on that line once "
             "the charges are confirmed with the government, then create the invoice."
    )
    gov_charge_is_known = fields.Boolean(
        string='Charge Amount is Fixed',
        default=False,
        help="When enabled, the government charge amount is pre-configured and known. "
             "On activation the line will be created with the fixed amount immediately, "
             "making it invoiceable without waiting for coordinator input."
    )
    gov_charge_amount = fields.Float(
        string='Fixed Gov. Charge Amount',
        digits='Product Price',
        default=0.0,
        help="The fixed government charge amount applied automatically on bundle activation. "
             "Only used when 'Charge Amount is Fixed' is enabled."
    )
    gov_charge_per_employee = fields.Float(
        string='Gov. Charge per Employee',
        digits='Product Price',
        default=0.0,
        help="Additional government charge applied per selected employee on activation. "
             "Total = Fixed Gov. Charge Amount + (number of selected employees × this value). "
             "Only used when 'Charge Amount is Fixed' and 'Requires Employee Selection' are both enabled."
    )

    # GOV-001: Government charges per activation (standalone request flow)
    wink_has_gov_charge = fields.Boolean(
        string='Gov. Charges (Standalone Request)',
        default=False,
        help='Enable when this service involves government fees (e.g. visa, license, trade license). '
             'If enabled, the customer will see the gov charge amount and a per-employee invoice '
             'will be generated upon activation request. Activation is blocked until payment is received.',
    )
    wink_default_gov_charge = fields.Monetary(
        string='Default Gov Charge per Employee',
        currency_field='currency_id',
        help='Default government charge per employee. The coordinator can override this at activation time. '
             'Total = this amount × number of selected employees.',
    )

    # EPIC-11: Catalogue report — live count of active subscriptions for this service
    wink_active_order_count = fields.Integer(
        compute='_compute_wink_active_order_count',
        string='Active Subscriptions',
        help='Number of confirmed sale orders (state=sale) where this product is the source service.',
    )

    def _compute_wink_active_order_count(self):
        groups = self.env['sale.order'].read_group(
            [('wink_source_product_id', 'in', self.ids), ('state', '=', 'sale')],
            ['wink_source_product_id'],
            ['wink_source_product_id'],
        )
        count_map = {g['wink_source_product_id'][0]: g['wink_source_product_id_count'] for g in groups}
        for product in self:
            product.wink_active_order_count = count_map.get(product.id, 0)


