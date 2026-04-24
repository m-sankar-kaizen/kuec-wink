# -*- coding: utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError


class TenderBidApproval(models.Model):
    _name = 'tender.bid.approval'
    _description = 'Tender Bid Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'tender_bid_id'

    tender_bid_id = fields.Many2one('tender.bid', string='Tender Bid')
    user_id = fields.Many2one('res.users', string="Responsible User")
    evaluation_type = fields.Selection([
        ('technical', 'Technical'),
        ('commercial', 'Commercial'),
    ], default='technical', string='Approval Type')

    def _get_default_signature(self):
        return self.user_id.display_name

    def sign_request(self):
        if self.env.user.id != self.user_id.id:
            raise UserError(_("You can't sign requests that are not your's"))
        else:
            self._check_and_raise_evaluation_rating()
            self.signature = self.env.user.sign_signature

    @api.depends('request_type', 'current_display_name')
    def _compute_reason(self):
        for record in self:
            record.reason = record.reason or ""

    def _check_and_raise_evaluation_rating(self):
        self.ensure_one()

        bid = self.tender_bid_id
        if not bid:
            return

        if self.evaluation_type == 'technical':
            checklists = bid.technical_evaluation_checklist_ids
            error_msg = _("All Technical rating scores must be greater than 0.")

        elif self.evaluation_type == 'commercial':
            checklists = bid.commercial_evaluation_checklist_ids
            error_msg = _("All Commercial rating scores must be greater than 0.")

        else:
            return

        if checklists.filtered(lambda r: r.rating_score <= 0):
            raise ValidationError(error_msg)
