from odoo import models, fields, _
from odoo.exceptions import ValidationError


class CWIPWizard(models.TransientModel):
    _name = 'cwip.wizard'
    _description = "CWIP Wizard"

    type = fields.Selection([
        ("cwip_as_fixed_asset", "CWIP as Fixed Asset"),
        ("cwip_to_fixed_asset", "Transfer CWIP to Fixed Asset")],
        required=True,
        default='cwip_as_fixed_asset')
    asset_model_id = fields.Many2one('account.asset',
                                     domain=lambda self: [('company_id', '=',
                                                           self.env.company.id),
                                                          ('state', '=', 'model')])
    cwip_journal_id = fields.Many2one('account.journal',
                                      domain=lambda self: [('company_id', '=',
                                                            self.env.company.id),
                                                           ('type', '=', 'general')],
                                      default=lambda self: self.env.company.cwip_journal_id.id)
    asset_name = fields.Char()

    company_id = fields.Many2one('res.company')

    def confirm(self):
        if self.type == 'cwip_as_fixed_asset':
            journal_items = self.env[
                'account.move.line'].browse(
                self._context.get('active_ids'))
            return journal_items.turn_as_asset()
        elif self.type == 'cwip_to_fixed_asset':
            if not self.asset_model_id.account_asset_id:
                raise ValidationError("Fixed asset account is not set in "
                                      "Asset Model.")
            journal_items = self.env['account.move.line'].browse(
                self._context.get('active_ids'))

            total_amount = sum(journal_items.mapped('debit')) + sum(journal_items.mapped('credit'))

            debit_line = {'account_id': self.asset_model_id.account_asset_id.id,
                          'debit': total_amount}

            credit_lines = []
            for line in journal_items:
                line_amount = line.credit + line.debit
                if line_amount:
                    credit_lines.append((0, 0, {
                        'account_id': line.account_id.id,
                        'credit': abs(line_amount),
                    }))

            print('debit_line', debit_line)
            print('credit_lines', credit_lines)

            journal_entry = self.env['account.move'].create({
                'move_type': 'entry',
                'company_id': self.env.company.id,
                'date': fields.Date.today(),
                'ref': 'Journal Created by CWIP Asset Transfer',
                'journal_id': self.cwip_journal_id.id,
                'line_ids': credit_lines + [(0, 0, debit_line)],
            })
            asset = self.env['account.asset'].sudo().create({
                'name': self.asset_name,
                'company_id': self.company_id.id,
                'original_value': total_amount,
                'model_id': self.asset_model_id.id,
                'account_asset_id': self.asset_model_id.account_asset_id.id,
                'cwip_move_id': journal_entry.id
            })
            asset._onchange_model_id()
            journal_entry.cwip_asset_id = asset.id
            return {
                "name": _("Turn as an asset"),
                "type": "ir.actions.act_window",
                "res_model": "account.asset",
                "views": [[False, "form"]],
                "target": "current",
                'res_id': asset.id,
            }
