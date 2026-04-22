# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    technical_score_weight = fields.Float(related='company_id.technical_score_weight',
                                          readonly=False)
    commercial_score_weight = fields.Float(related='company_id.commercial_score_weight',
                                           readonly=False)
    vendor_evaluation_reminder_days = fields.Integer(
        related='company_id.vendor_evaluation_reminder_days', readonly=False)

    support_email_address = fields.Char(related='company_id.support_email_address', readonly=False)
    vendor_procurement_policy_link = fields.Char(related='company_id.vendor_procurement_policy_link',
                                              readonly=False)
    purchase_material = fields.Html(
        related='company_id.purchase_material',
        readonly=False
    )
    purchase_service = fields.Html(
        related='company_id.purchase_service',
        readonly=False
    )

    contract_material = fields.Html(
        related='company_id.contract_material',
        readonly=False
    )
    contract_service = fields.Html(
        related='company_id.contract_service',
        readonly=False
    )

    blanket_material = fields.Html(
        related='company_id.blanket_material',
        readonly=False
    )
    blanket_service = fields.Html(
        related='company_id.blanket_service',
        readonly=False
    )
