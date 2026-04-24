from odoo import models, fields


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    budget_transfer_count = fields.Integer(
        'budget.transfer.request',
        compute='compute_transfer_counts')

    def compute_transfer_counts(self):
        for rec in self:
            rec.budget_transfer_count = self.env['budget.transfer.request'].sudo().search_count([(
                'requisition_id', '=', rec.id
            )])

    def show_related_transfers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Budget Transfer Requests',
            'res_model': 'budget.transfer.request',
            'domain': [('id', 'in', self.env['budget.transfer.request'].sudo().search([(
                'requisition_id', '=', self.id
            )]).ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }
    

