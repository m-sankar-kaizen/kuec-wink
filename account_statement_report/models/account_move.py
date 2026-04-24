# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'Account Move'

    description = fields.Text(compute='get_description')
    today_date = fields.Date(string="Today's Date", compute="_compute_today_date")

    @api.depends('name')  # You can use any dependency or leave it empty
    def _compute_today_date(self):
        for rec in self:
            rec.today_date = fields.Date.today()

    def get_description(self):
        for rec in self:
            description_text = ""
            for line in rec.line_ids:
                if line.product_id:
                    line_description = "{}  {}".format(line.product_id.name, line.quantity) or ""
                    description_text += line_description + "\n"
            rec.description = description_text
