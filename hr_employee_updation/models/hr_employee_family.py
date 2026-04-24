
from datetime import timedelta
from odoo import api, fields, models, _


class HrEmployeeFamily(models.Model):
    """Table for keep employee family information"""
    _name = 'hr.employee.family'
    _description = 'HR Employee Family Info'
    _rec_name = 'member_name'

    employee_id = fields.Many2one('hr.employee', string="Employee",
                                  help='Select corresponding Employee',
                                  invisible=1)
    relation_id = fields.Many2one('hr.employee.relation', string="Relation",
                                  help="Relationship with the employee")
    member_name = fields.Char(string='Name', help='Name of the family member')
    member_contact = fields.Char(string='Contact No',
                                 help='Contact No of the family member')
    birth_date = fields.Date(string="DOB", tracking=True,
                             help='Birth date of the family member')
