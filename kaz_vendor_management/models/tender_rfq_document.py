# -*- coding: utf-8 -*-
from odoo import models, fields, api


class TenderRFQDocument(models.Model):
    _name = 'tender.rfq.document'
    _description = 'Tender RFQ Document'
    _check_company_auto = True

    name = fields.Char(string='Name', required=True)
    file_name = fields.Char(string='File Name')
    attachment_id = fields.Binary(string='Attachments', required=True)
    available_online = fields.Boolean(string='Available Online', default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender RFQ')
