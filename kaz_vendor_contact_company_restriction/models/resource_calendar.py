# -*- coding: utf-8 -*-
from odoo import models, fields


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')