from odoo import models, fields


class HrDisciplinaryActionType(models.Model):
    _name = 'hr.disciplinary.action.type'
    _description = 'Disciplinary Action Type'

    name = fields.Char(string='Action Type Name', required=True)
    action_category_id = fields.Many2one('hr.disciplinary.action.category',
                                         string='Category', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)


class HrDisciplinaryActionCategory(models.Model):
    _name = 'hr.disciplinary.action.category'
    _description = 'Disciplinary Action Category'

    name = fields.Char(string='Category Name', required=True)
    active = fields.Boolean(string='Active',
                            default=True)