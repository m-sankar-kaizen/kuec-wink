# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acting_threshold_days = fields.Integer(string='Acting Delegation Threshold (Days)', default=5, config_parameter='hr_acting_delegation.threshold_days', help='After this number of days, a warning will suggest setting an acting delegation on the Time Off request.')
# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acting_delegation_validation = fields.Selection([
        ('blocking', 'Blocking'),
        ('warning', 'Warning'),
    ], string='Acting Delegation Validation', default='blocking', config_parameter='hr_acting_delegation.validation_type')

    acting_delegation_threshold_days = fields.Integer(string='Threshold Working Days', default=5, config_parameter='hr_acting_delegation.threshold_days')
