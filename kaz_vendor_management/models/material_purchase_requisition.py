# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError
from odoo.tools import format_date


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    requisition_type_id = fields.Many2one('purchase.requisition.type', string='Type')
    req_type = fields.Selection(related='requisition_type_id.requisition_type')
    is_tender = fields.Boolean(related='requisition_type_id.is_tender')
    material_attachment_line_ids = fields.One2many('material.attachment.line',
                                                   'purchase_requisition_id')
    attachment_line_generated = fields.Boolean(default=False, string='Attachment Line Generated')
    warning_message = fields.Char(string='Warning', compute="_compute_warning_messages", store=True)
    warning_message_html = fields.Html(string='Warning Explanation',
                                       compute="_compute_warning_messages", store=True)
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender RFQ',
                                    compute='_compute_tender_rfq_id')
    show_secondary_repeated_rfq = fields.Boolean(compute='_compute_show_secondary_repeated_rfq')
    show_tender_action = fields.Boolean(compute='_compute_show_tender_action')
    order_type = fields.Selection(
        selection=[
            ('material', 'Material Request'),
            ('service', 'Service Order'),
        ],
        string='Order Type',
    )

    @api.depends('requisition_type_id')
    def _compute_show_approve(self):
        """Override _compute_show_approve as 'type' field has
        been deprecated and 'requisition_type_id' field is being used instead"""
        for requisition in self:
            if requisition.requisition_type_id:
                work_flow = requisition.get_groups_flow()
                if requisition.approvement_state == 'pending':
                    group_name = requisition.get_group_name(work_flow[0])
                    if requisition.env.user.has_group(group_name):
                        requisition.show_approve = True
                        return
                elif requisition.approvement_state not in ['draft', 'pending', 'approved',
                                                           'completed', 'rejected']:
                    if requisition.current_group:
                        old_index = work_flow.index(requisition.current_group)
                        new_index = old_index + 1
                        if new_index < len(work_flow):
                            group_name = requisition.get_group_name(work_flow[new_index])
                            if requisition.env.user.has_group(group_name):
                                requisition.show_approve = True
                                return
            requisition.show_approve = False

    @api.depends(
        'requisition_type_id',
        'is_tender',
        'purchase_ids',
        'purchase_ids.state',
        'approvement_state'
    )
    def _compute_show_tender_action(self):
        for rec in self:
            show = rec.requisition_type_id.is_tender

            if rec.requisition_type_id.requisition_type == 'repeated':
                po_count = len(rec.purchase_ids)

                # Must have exactly one PO
                if po_count >= 2 and len(
                        rec.purchase_ids.filtered(lambda p: p.state == 'cancel')) >= 2:
                    show = not rec.tender_rfq_id
                else:
                    show = False

            if rec.is_tender:
                show = not rec.tender_rfq_id

            if rec.approvement_state != 'approved':
                show = False

            rec.show_tender_action = show

    @api.depends(
        'requisition_type_id',
        'is_tender',
        'purchase_ids',
        'purchase_ids.state',
        'approvement_state'
    )
    def _compute_show_secondary_repeated_rfq(self):
        for rec in self:
            show = True

            if rec.is_tender:
                show = False
            if rec.requisition_type_id.requisition_type != 'repeated':
                show = False

            po_count = len(rec.purchase_ids)

            # Must have exactly one PO
            if po_count != 1:
                show = False

            # That PO must be cancelled
            po = rec.purchase_ids[:1]
            if not po or po.state != 'cancel':
                show = False

            if rec.approvement_state != 'approved':
                show = False

            rec.show_secondary_repeated_rfq = show

    def action_create_rfq(self, partner_id):
        self.ensure_one()

        # Create the RFQ (Purchase Order)
        po_vals = {
            'custom_requisition_id': self.id,
            'purchase_manual_currency_rate': self.purchase_manual_currency_rate,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'partner_id': partner_id,
            'order_type': self.order_type,
            'order_line': [
                Command.create({
                    'product_id': rec.product_id.id,
                    'name': rec.product_id.name,
                    'account_id': rec.account_id.id,
                    'analytic_distribution': rec.analytic_distribution,
                    'product_qty': rec.qty,
                    'price_unit': rec.price_unit,
                })
                for rec in self.requisition_line_ids
            ],
        }

        purchase_order = self.env['purchase.order'].create(po_vals)
        self.purchase_ids = [Command.link(purchase_order.id)]

        # Return action to open the created RFQ
        return {
            'type': 'ir.actions.act_window',
            'name': _('RFQ'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': purchase_order.id,
            'views': [(False, 'form')],
        }

    def action_create_rfq_primary(self):
        self.ensure_one()
        return self.action_create_rfq(self.vendor_id.id)

    def get_next_best_vendor_from_tender(self):
        """Return the vendor (res.partner) who has the second-highest score
        in the tender related to this RFQ. If there are not enough bids,
        return an empty res.partner recordset.
        """
        vendor = self.env['res.partner']

        if not (self.purchase_id and self.purchase_id.tender_rfq_id):
            return vendor

        tender = self.purchase_id.tender_rfq_id

        # Get all bids sorted by total_score DESC
        bids = tender.tender_bid_ids.sorted(
            key=lambda b: b.total_score or 0,
            reverse=True
        )

        # Need at least 2 bids to get the "next best"
        if len(bids) < 2:
            return vendor

        second_best_bid = bids[1]

        if second_best_bid:
            return second_best_bid.partner_id

        return vendor

    def action_create_rfq_secondary(self):
        self.ensure_one()
        vendor = self.get_next_best_vendor_from_tender()
        if vendor:
            return self.action_create_rfq(vendor.id)
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Choose Vendor'),
                'res_model': 'choose.vendor',
                'view_mode': 'form',
                'target': 'new',
                'views': [(False, 'form')],
                'context': {
                    'default_material_purchase_requisition_id': self.id,
                }
            }

    def _compute_tender_rfq_id(self):
        for record in self:
            tender_rfq_id = record.env['tender.rfq'].sudo().search_fetch(
                domain=[('purchase_requisition_id', '=', record.id),
                        ('company_id', '=', record.company_id.id)],
                field_names=['id', 'name'],
                order='id desc',
                limit=1
            )
            tender_rfq_id = tender_rfq_id.id if tender_rfq_id else False
            record.tender_rfq_id = tender_rfq_id

    def action_open_tender(self):
        self.ensure_one()
        if self.tender_rfq_id:
            return {
                'type': 'ir.actions.act_window',
                'name': self.tender_rfq_id.name,
                'view_mode': 'form',
                'res_model': 'tender.rfq',
                'views': [(False, 'form')],
                'res_id': self.tender_rfq_id.id,
            }
        return None

    def action_create_tender(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tender RFQ'),
            'view_mode': 'form',
            'res_model': 'tender.rfq',
            'views': [(False, 'form')],
            'context': {
                'default_purchase_requisition_id': self.id,
                'default_manual_currency_rate': self.purchase_manual_currency_rate,
                'default_currency_id': self.currency_id.id,
                'default_order_type': self.order_type,
                'default_tender_rfq_line_ids': [
                    Command.create({
                        'product_id': rec.product_id.id,
                        'account_id': rec.account_id.id,
                        'analytic_distribution': rec.analytic_distribution,
                        'qty': rec.qty,
                        'price_unit': rec.price_unit,
                    }) for rec in self.requisition_line_ids
                ],
            },
        }

    @api.depends('requisition_line_ids', 'requisition_line_ids.product_id',
                 'requisition_line_ids.qty',
                 'requisition_line_ids.price_unit', 'purchase_id.order_line')
    def _compute_warning_messages(self):
        for rec in self:
            rec.warning_message = False
            rec.warning_message_html = False

            if not rec.purchase_id:
                continue

            po_lines = rec.purchase_id.order_line
            pr_to_po_logs = []
            po_to_pr_logs = []

            # PR → PO differences
            for req_line in rec.requisition_line_ids:
                po_line = po_lines.filtered(lambda l: l.product_id == req_line.product_id)
                product_display = req_line.product_id.display_name

                if not po_line:
                    pr_to_po_logs.append(
                        f"<li style='color:orange;'>Product <b>{product_display}</b> exists in PR but not in PO</li>"
                    )
                    continue

                po_line = po_line[0]

                # Quantity difference
                if float(po_line.product_qty) != float(req_line.qty):
                    color = 'green' if po_line.product_qty > req_line.qty else 'red'
                    pr_to_po_logs.append(
                        f"<li style='color:{color};'><b>{product_display}</b>: Quantity changed from {req_line.qty} → {po_line.product_qty}</li>"
                    )

                # Price difference
                if float(po_line.price_unit) != float(req_line.price_unit):
                    color = 'green' if po_line.price_unit > req_line.price_unit else 'red'
                    pr_to_po_logs.append(
                        f"<li style='color:{color};'><b>{product_display}</b>: Price changed from {req_line.price_unit} → {po_line.price_unit}</li>"
                    )

            # PO → PR differences (extra lines in PO)
            for po_line in po_lines:
                req_line = rec.requisition_line_ids.filtered(
                    lambda l: l.product_id == po_line.product_id)
                product_display = po_line.product_id.display_name
                if not req_line:
                    po_to_pr_logs.append(
                        f"<li style='color:orange;'>Product <b>{product_display}</b> exists in PO but not in PR</li>"
                    )

            # Populate fields if any differences
            if pr_to_po_logs or po_to_pr_logs:
                rec.warning_message = _(
                    "Warning: Differences detected in products, prices, or quantities.")

                html_content = "<p><b>Detected Differences:</b></p>"

                if pr_to_po_logs:
                    html_content += "<p><b>PR → PO:</b></p><ul>%s</ul>" % "".join(pr_to_po_logs)

                if po_to_pr_logs:
                    html_content += "<p><b>PO → PR:</b></p><ul>%s</ul>" % "".join(po_to_pr_logs)

                rec.warning_message_html = html_content
            else:
                rec.warning_message = False
                rec.warning_message_html = False

    @api.onchange('requisition_type_id')
    def _onchange_requisition_type(self):
        self.material_attachment_line_ids = [Command.clear()]
        self.attachment_line_generated = False

    def action_generate_attachment_lines(self):
        if self.requisition_type_id:
            self._check_total_amount()
            self.attachment_line_generated = True
            self.material_attachment_line_ids = [Command.clear()]
            if self.requisition_type_id.rq_type_attachment_line_ids:
                self.write({
                    'material_attachment_line_ids': [
                        Command.create({
                            'sequence': idx + 1,
                            'name': rec.name,
                            'attachment_is_required': rec.attachment_is_required,
                            'company_id': rec.company_id.id,
                            'attachment_type': rec.attachment_type,
                        }) for idx, rec in
                        enumerate(self.requisition_type_id.rq_type_attachment_line_ids) if rec.name
                    ]
                })

    def _validate_attachment_lines(self):
        self.ensure_one()
        for rec in self.material_attachment_line_ids:
            if rec.attachment_is_required:
                if rec.attachment_type == 'link' and not rec.attachment_link:
                    raise ValidationError(
                        _("One or More Attachment lines are missing required attachment link"))
                elif rec.attachment_type == 'attachment' and not rec.ir_attachment_ids:
                    raise ValidationError(
                        _("One or More Attachment lines are missing required attachments"))

    def _validate_requisition_type(self):
        self.ensure_one()
        if self.requisition_type_id:
            if self.requisition_type_id.is_justification_required and not self.reason:
                raise ValidationError(_("Reason for Requisition is Required"))
            if self.req_type == 'repeated' and self.purchase_id and self.purchase_id.date_approve:
                max_days = self.requisition_type_id.repeat_max_days or 0
                limit_date = fields.Date.today() - timedelta(days=max_days)
                po_date = self.purchase_id.date_approve.date() if hasattr(
                    self.purchase_id.date_approve, 'date') else self.purchase_id.date_approve

                if po_date < limit_date:
                    raise ValidationError(_(
                        "The selected PO cannot be older than %s days. "
                        "Approval date (%s) exceeds the allowed limit."
                    ) % (max_days, format_date(self.env, po_date)))

            if self.req_type == 'variation' and self.purchase_id:
                allowed_percent = self.requisition_type_id.variation_max_percent or 0
                if allowed_percent > 0:
                    po_amount = self.purchase_id.amount_total
                    allowed_limit = po_amount + (po_amount * allowed_percent / 100.0)

                    if self.total_amount > allowed_limit:
                        raise ValidationError(_(
                            "Total amount (%s) exceeds the allowed variation limit of %s%% on the original PO amount (%s). "
                            "Maximum allowed amount is %s."
                        ) % (self.total_amount,
                             allowed_percent,
                             po_amount,
                             allowed_limit
                             ))
        else:
            raise ValidationError(_("Requisition Type is mandatory"))

    def submit_to_approve(self):
        if not self.attachment_line_generated:
            raise ValidationError('Please Click On Generate Attachment Lines')
        if self.req_type == 'repeated':
            other_pr = self.sudo().search(
                [
                    ('company_id', '=', self.company_id.id),
                    ('purchase_id', '=', self.purchase_id.id),
                    ('id', '!=', self.id),
                ]
            )
            if other_pr:
                raise ValidationError(
                    _("You cannot create another PR of type 'Repeated' with the same Purchase Order."))
        self._check_total_amount()
        self._validate_attachment_lines()
        self._validate_requisition_type()
        super().submit_to_approve()

    # @api.constrains('total_amount', 'requisition_type_id')
    def _check_total_amount(self):
        for rec in self:
            rt = rec.requisition_type_id
            if not rt:
                continue

            if rt.value_min and rec.total_amount < rt.value_min:
                raise ValidationError(
                    _("Total amount cannot be less than the minimum allowed value (%s).") % rt.value_min)

            if rt.value_max and rec.total_amount > rt.value_max:
                raise ValidationError(
                    _("Total amount cannot exceed the maximum allowed value (%s).") % rt.value_max)

    def _fetch_additional_create_context(self):
        """To be supered to add for new purchase creates"""
        self.ensure_one()
        return {
            'order_type': self.order_type,
        }
