# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_invoices_ids = fields.Many2many('account.move', compute='_compute_partner_invoices')
    total_amount_untaxed_signed = fields.Monetary(compute="get_totals")
    total_amount_tax_signed = fields.Monetary(compute="get_totals")
    total_amount_total_signed = fields.Monetary(compute="get_totals")

    def _compute_partner_invoices(self):
        for rec in self:
            partner_invoices = self.env['account.move'].search(
                [('partner_id', '=', rec.id)]).filtered(
                lambda x: x.state == 'posted' and x.journal_id.name == 'Customer Invoices')
            credit_notes = partner_invoices.mapped('reversed_entry_id')
            rec.partner_invoices_ids = partner_invoices + credit_notes

    def get_totals(self):
        for rec in self:
            total_amount_untaxed_signed = 0
            total_amount_tax_signed = 0
            total_amount_total_signed = 0
            for line in rec.partner_invoices_ids:
                total_amount_untaxed_signed += line.amount_untaxed_signed
                total_amount_tax_signed += line.amount_tax_signed
                total_amount_total_signed += line.amount_total_signed
            rec.total_amount_untaxed_signed = total_amount_untaxed_signed
            rec.total_amount_tax_signed = total_amount_tax_signed
            rec.total_amount_total_signed = total_amount_total_signed
