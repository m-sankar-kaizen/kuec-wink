# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    draft_pr_pa_notify_days = fields.Integer(related='company_id.draft_pr_pa_notify_days',
                                             readonly=False)
    draft_pr_pa_notify_day = fields.Integer(related='company_id.draft_pr_pa_notify_day',
                                            readonly=False)
    draft_pr_pa_notify_month = fields.Selection(related='company_id.draft_pr_pa_notify_month',
                                                readonly=False)
