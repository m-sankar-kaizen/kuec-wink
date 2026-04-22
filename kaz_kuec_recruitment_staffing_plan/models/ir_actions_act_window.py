from odoo import models, api


class IrActionsWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.model
    def read(self, fields=None, load='_classic_read'):
        res = super().read(fields=fields, load=load)
        user = self.env.user
        is_manager = self.env['hr.department'].sudo().search([
                ('manager_id.user_id', '=', user.id),
                ('company_id', 'in', [self.env.company.id, False])
            ], limit=1)
        has_master_plan_access = user.has_group(
            'kaz_kuec_recruitment_staffing_plan.group_staffing_master')

        for action in res:
            if action.get('res_model') == 'hr.staffing.plan':
                if is_manager or has_master_plan_access:
                    action['context'] = "{'create': True}"
                else:
                    action['context'] = "{'create': False}"

        return res
