# -*- coding: utf-8 -*-
import base64

from datetime import timedelta

from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError


class TenderRFQ(models.Model):
    _name = 'tender.rfq'
    _description = 'Tender RFQ'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='TRFQ Number', readonly=True, copy=False, default='New')
    version = fields.Integer(string='Version', readonly=True, copy=False, default=1)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    title = fields.Char(string='Title', required=True)
    partner_category_ids = fields.Many2many('partner.category', required=True,
                                            string='Partner Category')
    partner_ids = fields.Many2many('res.partner', string="Partners")
    description = fields.Html(string='Scope of Work')
    portal_description = fields.Html(string='Portal Description', required=True)
    evaluation_criteria = fields.Html(string='Evaluation Criteria', required=True)
    submission_date = fields.Date(string='Submission Date', help="Tender is published Officially")
    expected_decision_date = fields.Date(string='Expected Decision Date',
                                         help="Date to review bids and choose the winner")
    delivery_date = fields.Date(string='Delivery Date',
                                help="Expected delivery or service completion date")
    bid_start_date = fields.Date(string='Bid Start Date',
                                 help="Vendors can start submitting their bids")
    kick_off_meeting_date = fields.Datetime(string='Kick Off Meeting Date', tracking=True,)
    bid_end_date = fields.Date(string='Bid End Date', help="Last date to submit bids")
    is_exclusive = fields.Boolean(string='Is Exclusive',
                                  help="Only Selected Vendors can Attend this Tender")
    responsible_user_id = fields.Many2one('res.users', string='Responsible User')
    is_bafo = fields.Boolean(string='Is BAFO', default=False)
    bafo_type = fields.Selection(
        selection=[
            ('all', 'All Vendors'),
            ('top_2', 'Top 2 Commercial Vendors'),
            # ('technical', 'Best Technical Vendors'),
            ('best_x', 'The Technical and Commercial offers'),
        ],
        string='BAFO Type',
    )
    purchase_requisition_id = fields.Many2one('material.purchase.requisition',
                                              string='Purchase Requisition')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('closed', 'Closed'),
            ('under_review', 'Under Review'),
            ('bafo', 'BAFO'),
            ('bafo_awarded', 'BAFO Awarded'),
            ('awarded', 'Awarded'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        string='Status',
        tracking=True,
    )
    tender_rfq_document_ids = fields.One2many('tender.rfq.document', 'tender_rfq_id',
                                              string='Tender RFQ Documents')
    technical_user_ids = fields.Many2many('res.users', 'tender_rfq_technical_user_rel',
                                          domain=lambda self: [('groups_id', 'in', self.env.ref(
                                              'base.group_user').ids)])
    commercial_user_ids = fields.Many2many('res.users', 'tender_rfq_commercial_user_rel',
                                           domain=lambda self: [('groups_id', 'in', self.env.ref(
                                               'base.group_user').ids)])
    technical_score_weight = fields.Float(
        string='Technical Score',
        help='Technical Score Weight, Percentage weight for Technical Evaluation (must total 100 with Commercial)',
        compute='_compute_scores',
        inverse='_inverse_technical_score',
        store=True,
    )
    commercial_score_weight = fields.Float(
        string='Commercial Score',
        help='Commercial Score Weight, Percentage weight for Commercial Evaluation (must total 100 with Technical)',
        compute='_compute_scores',
        inverse='_inverse_commercial_score',
        store=True,
    )
    technical_evaluation_checklist_id = fields.Many2one('evaluation.checklist.conf',
                                                        domain="[('evaluation_type', '=', 'technical'), ('state', '=', 'active')]",
                                                        string='Technical Evaluation Checklist')
    commercial_evaluation_checklist_id = fields.Many2one('evaluation.checklist.conf',
                                                         domain="[('evaluation_type', '=', 'commercial'), ('state', '=', 'active')]",
                                                         string='Commercial Evaluation Checklist')
    tender_bid_ids = fields.One2many('tender.bid', 'tender_rfq_id', string='Tender Bids')
    bid_count = fields.Integer(compute='_compute_bid_count', string='Bid Count')
    tender_bafo_request_ids = fields.One2many('tender.bafo.request', 'tender_rfq_id',
                                              string='Tender Bafo Requests')

    def _get_default_currency_rate(self):
        currency_rate = self.expected_currency_rate or 1
        if self.purchase_requisition_id:
            currency_rate = self.purchase_requisition_id.purchase_manual_currency_rate
        return currency_rate

    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    manual_currency_rate = fields.Float('Rate', digits=0,
                                        default=_get_default_currency_rate)
    company_currency_id = fields.Many2one(string='Company Currency',
                                          related='company_id.currency_id', readonly=True)
    expected_currency_rate = fields.Float(compute="_compute_expected_currency_rate", digits=0)
    tender_rfq_line_ids = fields.One2many('tender.rfq.line', 'tender_rfq_id',
                                          string='Tender RFQ Lines')
    total_amount = fields.Float(compute='_compute_total_amount', string='Total Amount', store=True)
    tender_rfq_id = fields.Many2one('tender.rfq', string='Parent Tender RFQ')
    tender_rfq_ids = fields.One2many('tender.rfq', 'tender_rfq_id', string='Tender RFQs')
    awarded_tender_bid_id = fields.Many2one('tender.bid', string='Awarded Tender Bid')
    child_tender_rfq_count = fields.Integer(compute='_compute_child_tender_rfq_count',
                                            string='Number of BAFO Tender')
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    tender_required_attachment_ids = fields.One2many('tender.required.attachment', 'tender_rfq_id',
                                                     string='Tender Required Attachments')
    tender_type = fields.Selection(
        selection=[
            ('purchase', 'Purchase Order'),
            ('contract', 'Contract Agreement'),
            ('blanket', 'Blanket Order'),
        ],
        string='Tender Type',
    )
    order_type = fields.Selection(
        selection=[
            ('material', 'Material Request'),
            ('service', 'Service Order'),
        ],
        string='Order Type',
    )
    contract_agreement_ids = fields.One2many('purchase.contract.agreement', 'tender_rfq_id',
                                             'Contract Agreement')
    contract_agreement_id = fields.Many2one('purchase.contract.agreement',
                                            'Active Contract Agreement')

    purchase_agreement_ids = fields.One2many('purchase.requisition', 'tender_rfq_id',
                                             string='Purchase Agreement')
    purchase_agreement_id = fields.Many2one('purchase.requisition',
                                            'Active Purchase Agreement')

    def action_create_blanket_order(self):
        self.ensure_one()
        for rec in self.purchase_agreement_ids:
            if rec.state != 'cancel':
                raise ValidationError(_(
                    "You cannot create a new blanket order because an existing blanket order is already in '%s' state."
                ) % rec.state.title())
        contract = self.company_id.blanket_material if self.order_type == 'material' else self.company_id.blanket_service
        return {
            'type': 'ir.actions.act_window',
            'name': _("Contract Agreement"),
            'view_mode': 'form',
            'res_model': 'purchase.requisition',
            'views': [(False, 'form')],
            'context': {
                'default_tender_rfq_id': self.id,
                'default_currency_id': self.currency_id.id,
                'default_tender_bid_id': self.awarded_tender_bid_id.id,
                'default_vendor_id': self.awarded_tender_bid_id.partner_id.id,
                'default_description': contract,
                'default_order_type': self.order_type,
                'default_user_id': self.responsible_user_id.id,
                'default_date_start': self.delivery_date,
                'default_requisition_type': 'blanket_order',
                'default_line_ids': [
                    Command.create({
                        'product_id': line.product_id.id,
                        # 'account_id': line.account_id.id,
                        'analytic_distribution': line.analytic_distribution,
                        'product_qty': line.qty,
                        'price_unit': line.price_unit,
                    }) for line in self.awarded_tender_bid_id.tender_bid_rfq_line_ids
                ],
            }
        }

    def action_open_blanket_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Blanket Order"),
            'view_mode': 'list,form',
            'res_model': 'purchase.requisition',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.purchase_agreement_ids.ids)],
            'context': {
                'create': False,
            }
        }

    def action_open_contract_agreement(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Contract Agreement"),
            'view_mode': 'list,form',
            'res_model': 'purchase.contract.agreement',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.contract_agreement_ids.ids)],
            'context': {
                'create': False,
            }
        }

    def action_create_contract_agreement(self):
        self.ensure_one()
        for rec in self.contract_agreement_ids:
            if rec.state in ['draft', 'approved']:
                raise ValidationError(_(
                    "You cannot create a new contract because an existing agreement is already in '%s' state."
                ) % rec.state.title())
        contract = self.company_id.contract_material if self.order_type == 'material' else self.company_id.contract_service
        return {
            'type': 'ir.actions.act_window',
            'name': _("Contract Agreement"),
            'view_mode': 'form',
            'res_model': 'purchase.contract.agreement',
            'views': [(False, 'form')],
            'context': {
                'default_tender_rfq_id': self.id,
                'default_currency_id': self.currency_id.id,
                'default_tender_bid_id': self.awarded_tender_bid_id.id,
                'default_terms_and_condition': contract,
                'default_order_type': self.order_type,
                'default_contract_agreement_line_ids': [
                    Command.create({
                        'product_id': line.product_id.id,
                        'account_id': line.account_id.id,
                        'analytic_distribution': line.analytic_distribution,
                        'qty': line.qty,
                        'required_qty': line.required_qty,
                        'price_unit': line.price_unit,
                        'expected_price_unit': line.expected_price_unit,
                        'amount_in_currency': line.amount_in_currency,
                    }) for line in self.awarded_tender_bid_id.tender_bid_rfq_line_ids
                ],
            }
        }

    @api.constrains('is_exclusive', 'partner_ids')
    def _check_exclusive_partner_logic(self):
        for rec in self:
            # Case 1: Not exclusive but partners selected
            if not rec.is_exclusive and rec.partner_ids:
                raise ValidationError(
                    _("This tender is not exclusive. Please remove all selected partners.")
                )
            # Case 2: Exclusive but no partners selected
            if rec.is_exclusive and not rec.partner_ids:
                raise ValidationError(
                    _("Exclusive tenders must have at least one partner.")
                )

    def unlink(self):
        for tender in self:
            if tender.state != 'draft':
                raise UserError(_("You cannot delete a Tender while it's not in draft state."))
        return super().unlink()

    @api.depends('tender_rfq_line_ids', 'tender_rfq_line_ids.qty', 'tender_rfq_line_ids.price_unit')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.tender_rfq_line_ids.mapped('amount_in_currency'))

    @api.depends('tender_rfq_document_ids')
    def _compute_child_tender_rfq_count(self):
        for doc in self:
            doc.child_tender_rfq_count = len(doc.tender_rfq_ids.ids)

    def copy(self, default=None):
        if self.tender_rfq_id:
            raise ValidationError(_("You cannot duplicate an BAFO Tender"))
        else:
            default = dict(default or {})
            default.update({
                'purchase_requisition_id': False,
                'purchase_id': False,
                'awarded_tender_bid_id': False,
                'contract_agreement_id': False,
            })
            return super().copy(default=default)

    def _get_child_trender_data(self):
        datas = self.copy_data()
        last_version = len(self.tender_rfq_ids.ids) + 2
        rfq_lines = self.tender_rfq_line_ids.copy_data()
        tender_rfq_document_lines = self.tender_rfq_document_ids.copy_data()
        for data in datas:
            data.update({
                'tender_rfq_id': self.id,
                'version': last_version,
                'tender_rfq_line_ids': [
                    Command.create(line) for line in rfq_lines
                ],
                'tender_rfq_document_ids': [
                    Command.create(line) for line in tender_rfq_document_lines
                ]
            })
            last_version += 1
        return datas

    def action_open_purchase(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchase Order"),
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'views': [(False, 'form')],
            'res_id': self.purchase_id.id,
        }

    def action_create_purchase(self):
        self.ensure_one()
        self.awarded_tender_bid_id._action_create_purchase_order()

    def action_update_kick_off_meeting_date(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Kick Off Meeting Date"),
            'view_mode': 'form',
            'res_model': 'kick.off.meeting',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_tender_rfq_id': self.id,
            }
        }

    def action_send_award_letter(self):
        self.ensure_one()
        if not self.kick_off_meeting_date:
            raise UserError("Kick Off Meeting Date is required.")

        pdf_content, _ = self.env['ir.actions.report'].with_company(
            self.company_id
        )._render_qweb_pdf('kaz_vendor_management.action_report_awarding_letter_report', res_ids=self.awarded_tender_bid_id.ids)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f"Awarding Letter - {self.display_name}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        ctx = {
            'default_model': 'tender.bid',
            'default_res_ids': self.awarded_tender_bid_id.ids,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_light',
            'email_notification_allow_footer': True,
            'default_partner_ids': self.awarded_tender_bid_id.partner_id.ids,
            'default_attachment_ids': [Command.link(attachment.id)],
        }
        if len(self) > 1:
            ctx['default_composition_mode'] = 'mass_mail'
        else:
            ctx.update({
                'force_email': True,
            })
            mail_template = self.env.ref('kaz_vendor_management.mail_template_tender_awarded',
                                         raise_if_not_found=False)
            if mail_template:
                ctx.update({
                    'default_template_id': mail_template.id,
                    'mark_so_as_sent': True,
                })
            if mail_template and mail_template.lang:
                lang = mail_template._render_lang(self.ids)[self.id]
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
        if self.env.is_admin():
            layout_action = self.env['ir.actions.report']._action_configure_external_report_layout(
                action,
            )
            # Need to remove this context for windows action
            action.pop('close_on_report_download', None)
            layout_action['context']['dialog_size'] = 'extra-large'
            return layout_action
        return action

    def action_open_awarded_bid(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Awarded Bid"),
            'view_mode': 'form',
            'res_model': 'tender.bid',
            'views': [(False, 'form')],
            'res_id': self.awarded_tender_bid_id.id,
        }

    def action_parent_tender(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Parent Tender"),
            'view_mode': 'form',
            'res_model': 'tender.rfq',
            'views': [(False, 'form')],
            'res_id': self.tender_rfq_id.id,
        }

    def action_child_tenders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("BAFO Tenders"),
            'view_mode': 'kanban,list,form',
            'res_model': 'tender.rfq',
            'views': [(False, 'kanban'), (False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.tender_rfq_ids.ids)],
            'order': 'version desc',
        }

    @api.constrains('manual_currency_rate')
    def _check_currency_rate(self):
        """Ensure the currency rate is strictly positive when record's currency differs from company currency."""
        for rec in self:
            if (
                    rec.currency_id
                    and rec.company_id
                    and rec.currency_id != rec.company_currency_id
                    and rec.manual_currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    @api.onchange('currency_id', 'company_id')
    def _onchange_currency_id_set_manual_rate(self):
        """
        When the currency or company changes, suggest the standard
        conversion rate in the manual rate field.
        """
        self.manual_currency_rate = self.expected_currency_rate

    def refresh_currency_rate(self):
        for so in self:
            so.manual_currency_rate = so.expected_currency_rate

    @api.depends('currency_id', 'company_currency_id', 'company_id')
    def _compute_expected_currency_rate(self):
        for so in self:
            if so.currency_id:
                so.expected_currency_rate = so.env['res.currency']._get_conversion_rate(
                    from_currency=so.company_currency_id,
                    to_currency=so.currency_id,
                    company=so.company_id,
                    date=fields.Date.context_today(self),
                )
            else:
                so.expected_currency_rate = 1

    def get_currency_rate(self, company_id, to_currency_id, date):
        company = self.env['res.company'].browse(company_id)
        to_currency = self.env['res.currency'].browse(to_currency_id)

        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    @api.constrains('partner_ids', 'is_exclusive')
    def _constrains_partner_id(self):
        for record in self:
            if record.is_exclusive:
                for partner in record.partner_ids:
                    if partner.state != 'approved':
                        raise ValidationError(
                            "The Partner must be in 'Approved' state to be selected in this Tender.")
                    if partner.has_expired_documents:
                        raise ValidationError(
                            "You cannot choose a partner who has expired documents, Please update the expired documents.")

    @api.depends('tender_bid_ids')
    def _compute_bid_count(self):
        for tender in self:
            tender.bid_count = len(tender.tender_bid_ids.ids)

    def action_open_purchase_requisition(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchase Requisition"),
            'view_mode': 'form',
            'res_model': 'material.purchase.requisition',
            'views': [(False, 'form')],
            'res_id': self.purchase_requisition_id.id,
        }

    def action_open_bid(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tender Bids"),
            'view_mode': 'list,form',
            'res_model': 'tender.bid',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('tender_rfq_id', '=', self.id)],
            'order': 'total_score desc'
        }

    def action_create_bid(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tender Bid"),
            'view_mode': 'form',
            'res_model': 'tender.bid',
            'views': [(False, 'form')],
            'context': {
                'default_tender_rfq_id': self.id,
                'default_currency_id': self.currency_id.id,
                'default_manual_currency_rate': self.manual_currency_rate,
            }
        }

    def action_send_notification_mail(self):
        self.ensure_one()

        template = self.env.ref('kaz_vendor_management.mail_template_tender_active',
                                raise_if_not_found=False)
        if not template:
            raise UserError(_("Mail template not found. Please contact Administrator."))

        partners = self._get_target_partners()
        if not partners:
            raise UserError(_("No vendors found to notify."))

        for partner in partners:
            if not partner.email:
                continue
            email_values = {
                'email_to': partner.email
            }
            context = {
                'partner': partner.name,
            }
            template.with_context(context).send_mail(self.id, email_values=email_values)

        return True

    def _get_target_partners(self):
        return self.env['res.partner'].search([
            ('is_vendor', '=', True),
            ('state', '=', 'approved'),
            ('partner_category_ids', 'in', self.partner_category_ids.ids)
        ]) if not self.is_exclusive else self.partner_ids

    def _validate_rfq_line(self):
        self.ensure_one()
        if not self.tender_rfq_line_ids:
            raise UserError(_("No Requisition lines found."))
        for line in self.tender_rfq_line_ids:
            if line.qty <= 0:
                raise UserError(_("Requisition line Quantity must be positive."))
            if line.price_unit <= 0:
                raise UserError(_("Requisition line Price unit must be positive."))

    def action_activate(self):
        self.ensure_one()
        self._validate_rfq_line()
        self.state = 'active'

    def action_cancel(self):
        self.ensure_one()
        active_bafo = self.tender_rfq_ids.filtered(lambda r: r.state != 'cancelled')
        if active_bafo:
            raise UserError(_(
                "There are active BAFO tenders associated with this tender. "
                "Please cancel them before cancelling this tender."
            ))

        self.state = 'cancelled'
        self.tender_bid_ids.write({'state': 'rejected'})

    def action_reset_to_draft(self):
        self.ensure_one()

        if not self.state == 'cancelled' and self.tender_bid_ids:
            raise UserError(
                _("You cannot reset this Tender back to draft since there are active bids for this tender."))

        if self.state == 'cancelled' and self.tender_rfq_id:
            parent = self.tender_rfq_id
            other_children = parent.tender_rfq_ids - self

            if parent.state == 'bafo_awarded':
                raise UserError(_(
                    "The parent tender is BAFO-awarded. You cannot reset this tender to draft."
                ))

            if other_children.filtered(lambda c: c.state != 'cancelled'):
                raise UserError(_(
                    "There are other active BAFO tenders under the parent tender. "
                    "You cannot reset this tender to draft."
                ))

        elif self.state == 'awarded':
            raise UserError(_(
                "An awarded tender cannot be reset to draft."
            ))

        elif self.state == 'bafo_awarded':
            raise UserError(_(
                "A BAFO-awarded tender cannot be reset to draft."
            ))

        # reset
        self.state = 'draft'
        self.tender_bid_ids.write({'state': 'draft'})

    def action_tender_close(self):
        """Closes the Tender"""
        self.ensure_one()
        if self.purchase_requisition_id and not self.tender_rfq_id:
            required_min_bids = self.purchase_requisition_id.requisition_type_id.min_bids
            number_of_bids = self.bid_count
            if number_of_bids < required_min_bids:
                raise UserError(_(
                    "Cannot close the tender. The number of bids (%s) is less than the required minimum (%s)."
                    % (number_of_bids, required_min_bids)
                ))
        self.state = 'closed'

    def _notify_technical_commercial_users(self):
        """Create activities for all assigned technical and commercial users."""
        activity_type = self.env.ref(
            'kaz_vendor_management.mail_activity_type_tender')  # replace with your module name
        for user in self.technical_user_ids | self.commercial_user_ids:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=user.id,
                note=f"Please review the bids for tender '{self.name}' and provide your evaluation.",
                date_deadline=self.expected_decision_date or fields.Date.today() + timedelta(days=3)
            )

    def _close_activity(self,
                        activity_type_xml_id='kaz_vendor_management.mail_activity_type_tender'):
        """Closes the activity"""
        self.ensure_one()
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)
        if activity_type:
            activities = self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done')
            ])
            activities.action_feedback()

    def action_open_bafo_bid(self):
        self.ensure_one()
        field_name = 'total_score' if self.bafo_type != 'technical' else 'total_technical_score'
        return {
            'type': 'ir.actions.act_window',
            'name': _("BAFO Tender Bids"),
            'view_mode': 'list,form',
            'res_model': 'tender.bid',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('tender_rfq_id', '=', self.id), ('state', '=', 'bafo_selected')],
            'order': f'{field_name} desc',
        }

    def action_tender_under_review(self):
        """Tender under review"""
        self.ensure_one()
        self._notify_technical_commercial_users()
        self.state = 'under_review'

    def _get_top_and_rejected_bid(self, bafo_type=False):
        """Tender evaluate bid"""
        self.ensure_one()
        bafo_type = bafo_type or self.bafo_type
        top_bids = self.env['tender.bid']
        if bafo_type == 'all':
            top_bids = self.tender_bid_ids
        elif bafo_type == 'top_2':
            bids_sorted = self.tender_bid_ids.sorted(key=lambda b: b.total_commercial_score or 0,
                                                     reverse=True)
            if bids_sorted:
                # Take the top score
                first_score = bids_sorted[0].total_commercial_score or 0
                top_bids = bids_sorted.filtered(lambda b: b.total_commercial_score == first_score)
                if len(top_bids) < 2 and len(bids_sorted) > len(top_bids):
                    # Include second highest score
                    second_score = bids_sorted[len(top_bids)].total_commercial_score or 0
                    top_bids |= bids_sorted.filtered(
                        lambda b: b.total_commercial_score == second_score)
        elif bafo_type == 'best_x':
            bids_sorted = self.tender_bid_ids.sorted(key=lambda b: b.total_score or 0, reverse=True)
            if bids_sorted:
                # Take the top score
                first_score = bids_sorted[0].total_score or 0
                top_bids = bids_sorted.filtered(lambda b: b.total_score == first_score)
                if len(top_bids) < 2 and len(bids_sorted) > len(top_bids):
                    # Include second highest score
                    second_score = bids_sorted[len(top_bids)].total_score or 0
                    top_bids |= bids_sorted.filtered(lambda b: b.total_score == second_score)
        elif bafo_type == 'technical':
            bids_sorted = self.tender_bid_ids.sorted(key=lambda b: b.total_technical_score or 0,
                                                     reverse=True)
            if bids_sorted:
                top_score = bids_sorted[0].total_technical_score or 0
                top_bids = bids_sorted.filtered(lambda b: b.total_technical_score == top_score)
        rejected_bids = self.tender_bid_ids - top_bids
        return top_bids, rejected_bids

    def _validate_bids(self):
        non_evaluated_bids = self.tender_bid_ids.filtered(lambda bid: bid.state == 'evaluation')
        if non_evaluated_bids:
            raise ValidationError(
                _('There are Bids yet to be reviewed. Please review the bids.'))

    def action_award_tender(self):
        self.ensure_one()
        self._validate_bids()
        self._validate_bafo_request()
        self._close_activity()
        action = self.env['ir.actions.actions']._for_xml_id(
            'kaz_vendor_management.action_award_tender_wizard')
        return action

    def action_create_tender_bafo(self):
        self.ensure_one()
        self._validate_bids()
        existing_draft_rq = self.tender_bafo_request_ids.filtered(lambda r: r.state == 'draft')
        if existing_draft_rq:
            raise UserError(
                _("A draft BAFO request already exists for this tender. "
                  "Please cancel or approve the existing BAFO request before creating a new one.")
            )
        existing_active_child_tender = self.tender_rfq_ids.filtered(
            lambda r: r.state != 'cancelled')
        if existing_active_child_tender:
            raise UserError(
                _("An Active BAFO Tender already exists for this Tender. ")
            )
        self._close_activity()
        return {
            'type': 'ir.actions.act_window',
            'name': _("BAFO Tender Request"),
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'tender.bafo.request',
            'views': [(False, 'form')],
            'context': {
                'default_tender_rfq_id': self.id,
            }
        }

    def _validate_bafo_request(self):
        self.ensure_one()
        for rec in self.tender_bafo_request_ids:
            if rec.state == 'draft':
                raise ValidationError(
                    _('There are pending BAFO requests for this tender. Please approve or cancel it to move forward.'))

    def action_tender_bafo(self):
        """Tender bafo"""
        self.ensure_one()
        self._validate_bafo_request()
        if not self.tender_rfq_id:
            # self.state = 'bafo'
            return self.action_create_tender_bafo()
        return False

    @api.depends('technical_score_weight', 'commercial_score_weight')
    def _compute_scores(self):
        """Ensure both always add up to 100. If one is missing, assume default 50/50."""
        for rec in self:
            # Initialize defaults only if both are empty
            if not rec.technical_score_weight and not rec.commercial_score_weight:
                technical_score_weight = rec.company_id.technical_score_weight
                commercial_score_weight = rec.company_id.commercial_score_weight
                rec.technical_score_weight = technical_score_weight
                rec.commercial_score_weight = commercial_score_weight
            else:
                # Normalize total to 100
                total = rec.technical_score_weight + rec.commercial_score_weight
                if total != 100:
                    # Keep technical as is, fix commercial
                    rec.commercial_score_weight = 100 - rec.technical_score_weight

    def _inverse_technical_score(self):
        """When user modifies technical score, automatically recalc commercial."""
        for rec in self:
            if rec.technical_score_weight < 0:
                rec.technical_score_weight = 0
            if rec.technical_score_weight > 100:
                rec.technical_score_weight = 100
            rec.commercial_score_weight = 100 - rec.technical_score_weight

    def _inverse_commercial_score(self):
        """When user modifies commercial score, automatically recalc technical."""
        for rec in self:
            if rec.commercial_score_weight < 0:
                rec.commercial_score_weight = 0
            if rec.commercial_score_weight > 100:
                rec.commercial_score_weight = 100
            rec.technical_score_weight = 100 - rec.commercial_score_weight

    @api.constrains('technical_score_weight', 'commercial_score_weight')
    def _check_score_weights(self):
        for rec in self:
            total = (rec.technical_score_weight or 0) + (rec.commercial_score_weight or 0)
            if total != 100:
                raise ValidationError(
                    _("The total of Technical Score Weight and Commercial Score Weight must always be 100.")
                )

    def action_send_bafo_mail(self):
        """Send BAFO notification to vendors. Handles multiple tender records."""
        template = self.env.ref('kaz_vendor_management.mail_template_tender_bafo',
                                raise_if_not_found=False)
        if not template:
            raise UserError(_("Mail template not found. Please contact Administrator."))
        top_bids, rejected_bids = self.tender_rfq_id._get_top_and_rejected_bid()
        for bid in top_bids:
            partner = bid.partner_id
            if not partner:
                raise UserError(_("No vendors found to notify for tender '%s'." % bid.name))
            if not partner.email:
                continue
            email_values = {
                'email_to': partner.email
            }
            context = {
                'partner': partner.name,
                'bid_reference': bid.name,
            }
            template.with_context(context).send_mail(bid.id, email_values=email_values)
        return True

    @api.constrains('submission_date', 'delivery_date')
    def _check_submission_delivery_date(self):
        for record in self:
            if record.delivery_date < record.submission_date:
                raise ValidationError(_("Delivery date must be greater than submission date"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('tender.rfq') or 'New'
        return super().create(vals_list)

    @property
    def _tender_website_read_fields(self):
        return [
            'create_date', 'name', 'id', 'title', 'bid_start_date', 'bid_end_date',
            'submission_date', 'portal_description', 'evaluation_criteria', 'is_exclusive',
            'partner_category_ids', 'expected_decision_date', 'delivery_date', 'tender_rfq_id',
            'version', 'state', 'total_amount', 'currency_id',
        ]

    @property
    def _tender_website_read_o2m_fields(self):
        return {
            'tender_rfq_line_ids': [
                'id', 'name', 'product_id', 'qty', 'price_unit', 'uom_id'
            ],
            'tender_rfq_ids': [
                'id', 'name', 'state', 'version'
            ],
            'tender_rfq_document_ids': [
                'id', 'name', 'available_online'
            ]
        }

    def _read_tender_for_website(self):
        self.ensure_one()
        record = self.read(self._tender_website_read_fields)[0]
        o2m_fields = self._tender_website_read_o2m_fields
        record.update({
            'tender_rfq_line_ids': self.tender_rfq_line_ids.read(o2m_fields['tender_rfq_line_ids']),
            'tender_rfq_ids': self.tender_rfq_ids.read(o2m_fields['tender_rfq_ids']),
            'tender_rfq_document_ids': self.tender_rfq_document_ids.filtered(
                lambda rec: rec.available_online).read(o2m_fields['tender_rfq_document_ids']),
        })
        return record
