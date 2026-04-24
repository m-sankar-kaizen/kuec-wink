# -*- coding: utf-8 -*-
from odoo import models, fields


class KPIProvider(models.Model):
    # Deprecated
    _name = "kpi.provider"
    _description = "KPI Provider"

    name = fields.Char()
