# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class PurchaseContractAgreement(models.Model):
    _name = 'purchase.contract.agreement'
    _description = 'Purchase Contract Agreement'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='PA Number', readonly=True, copy=False, default='New')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    partner_id = fields.Many2one('res.partner', string='Partner',
                                 related='tender_bid_id.partner_id')
    user_id = fields.Many2one('res.users', string='User', related='tender_bid_id.bid_user_id')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    terms_and_condition = fields.Html(string='Terms and Condition')
    contract_attachment = fields.Binary(string='Contract Attachment')
    contract_agreement_line_ids = fields.One2many('purchase.contract.agreement.line',
                                                  'contract_agreement_id',
                                                  string='Purchase Contract Agreement Lines')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    purchase_id = fields.Many2one(related='tender_rfq_id.purchase_id', string='Purchase')
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender')
    tender_bid_id = fields.Many2one('tender.bid', string='Tender Bid')
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('pending', 'Submitted'), ('approved', 'Approved'),
                   ('rejected', 'Rejected')],
        default='draft',
    )
    order_type = fields.Selection(
        selection=[
            ('material', 'Material Request'),
            ('service', 'Service Order'),
        ],
        string='Order Type',
    )

    def submit_to_approve(self):
        self.ensure_one()
        if not self.contract_attachment:
            raise UserError(_("Please Attach the Contract Agreement before submitting."))
        self.state = 'pending'

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date > rec.end_date:
                raise ValidationError(_("The End Date cannot be earlier than the Start Date."))

    def action_approve(self):
        self.ensure_one()
        if not self.contract_attachment:
            raise ValidationError(_("Please Attach the Contract before Approving."))
        self.state = 'approved'
        self.tender_rfq_id.contract_agreement_id = self.id

    def action_reject(self):
        self.ensure_one()
        self.state = 'rejected'

    @api.depends('contract_agreement_line_ids', 'contract_agreement_line_ids.amount_in_currency')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.contract_agreement_line_ids.mapped('amount_in_currency'))

    def copy(self, default=None):
        raise UserError(_('You cannot copy this Purchase Contract Agreement'))

    def action_create_purchase(self):
        self.ensure_one()
        return self.tender_rfq_id.action_create_purchase()

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

    def action_open_tender_bid(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tender Bid"),
            'view_mode': 'form',
            'res_model': 'tender.bid',
            'views': [(False, 'form')],
            'res_id': self.tender_bid_id.id,
        }

    def action_open_tender(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tender"),
            'view_mode': 'form',
            'res_model': 'tender.rfq',
            'views': [(False, 'form')],
            'res_id': self.tender_rfq_id.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'purchase.contract.agreement') or 'New'
        return super().create(vals_list)
