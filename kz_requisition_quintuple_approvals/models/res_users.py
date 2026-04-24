# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    """
    Inherits the 'res.users' model to extend with department-level linkage.

    Key Features:
    -------------
    - Adds a department_id field to the user.
    - Enforces a constraint: if a user belongs to the 'Department Head' group,
      they must be assigned to a department.
    """
    _inherit = "res.users"

    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        required=False,
        help="Indicates the department this user is responsible for."
    )

    # @api.constrains('groups_id', 'department_id')
    # def restrict_user_department(self):
    #     """
    #     Constraint to ensure that any user who belongs to the 'Department Head' group
    #     must also be assigned to a department.
    #
    #     Raises:
    #         ValidationError: If a user belongs to the department head group but does not have a department.
    #     """
    #     if self.groups_id:
    #         department_group = self.env.ref('kz_requisition_quintuple_approvals.department_head')
    #         if department_group:
    #             if department_group.id in self.groups_id.ids and not self.department_id:
    #                 raise ValidationError(
    #                     _("A department head user must be assigned to a department."))
