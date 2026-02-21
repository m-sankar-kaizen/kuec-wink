# -*- coding: utf-8 -*-

from odoo import models, fields

class KuecDepartment(models.Model):
    _name = 'kuec.department'
    _description = 'KUEC Department'

    name = fields.Char(string='Name', required=True, translate=True)
    active = fields.Boolean(default=True)

class KuecServiceNature(models.Model):
    _name = 'kuec.service.nature'
    _description = 'KUEC Service Nature'

    name = fields.Char(string='Nature Name', required=True, translate=True)
    active = fields.Boolean(default=True)
