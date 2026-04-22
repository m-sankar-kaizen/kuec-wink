from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_department_manager = fields.Boolean(
        compute='_compute_is_department_manager',
        store=False
    )

    @api.depends_context('company', 'uid')
    def _compute_is_department_manager(self):
        for user in self:
            dept_manager = self.env['hr.department'].sudo().search([
                ('manager_id.user_id', '=', user.id),
                ('company_id', 'in', [self.env.company.id, False])
            ], limit=1)
            user.is_department_manager = bool(dept_manager)
