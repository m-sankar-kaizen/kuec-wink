from odoo import models, fields, _
from math import floor


class HREmployeeSettlements(models.Model):
    _inherit = 'hr.employee.settlements'

    resignation_form_id = fields.Many2one('register.form')
    exit_interview_id = fields.Many2one('exit.interview')
    exit_clearance_id = fields.Many2one('exit.clearance')

    company_code = fields.Selection(related='company_id.company_code')

    kuec_settlement_amount = fields.Monetary(readonly=True,
                                             currency_field='currency_id',
                                             default=0.0,
                                             string='KUEC Settlement Amount',
                                             )

    def action_view_resignation_form(self):
        action = self.env.ref('kaz_kuec_offboarding.action_ank_register_form').read()[0]
        action.update({
            "views": [[self.env.ref(
                'kaz_kuec_offboarding.register_form_form_view').id, "form"]],
            "view_mode": "form",
            "view_id": self.env.ref(
                'kaz_kuec_offboarding.register_form_form_view').id,
            "res_id": self.resignation_form_id.id,
            "context": {"create": False},
        })
        return action

    def action_view_exit_clearance(self):
        action = self.env.ref('kaz_kuec_offboarding.exit_clearance_form').read()[0]
        action.update({
            "res_id": self.exit_clearance_id.id,
            "context": {"create": False},
        })
        return action

    def action_view_exit_interview(self):
        action = self.env.ref('kaz_kuec_offboarding.exit_interview_form').read()[0]
        action.update({
            "res_id": self.exit_interview_id.id,
            "context": {"create": False},
        })
        return action

    def action_compute_settlement(self):
        res = super().action_compute_settlement()
        for rec in self:
            if rec.company_code != 'KUEC':
                continue
            years_worked = int(rec.years_worked) or 0.0
            basic = rec.basic_contract or 0.0
            total_amount = 0.0

            conditions = rec.company_id.kuec_settlement_conditions.sorted(
                key=lambda c: c.year_start or 0
            )
            for condition in conditions:
                start = condition.year_start or 0
                end = condition.year_end or float('inf')

                if years_worked <= start:
                    continue

                # Years applicable in this slab
                slab_years = min(years_worked, end) - start
                if slab_years <= 0:
                    continue

                total_amount += slab_years * basic * condition.amount
                print('slab_years', slab_years, 'total_amount', total_amount)

            rec.kuec_settlement_amount = total_amount
        return res

            # if rec.company_code == 'KUEC':
            #     if rec.company_id.kuec_settlement_conditions:
            #         amount = 0.0
            #         years = rec.years_worked or 0.0
            #         basic = rec.basic_contract or 0.0
            #         for condition in rec.company_id.kuec_settlement_conditions:
            #             start_year = condition.year_start or 0
            #             end_year = condition.year_end or float('inf')
            #             if start_year < years <= end_year:
            #                 applicable_years = min(years, end_year) - start_year
            #                 amount += applicable_years * basic * condition.amount
            #         rec.kuec_settlement_amount = amount
                # amount = 0.0
                # years = rec.years_worked or 0.0
                # basic = rec.basic_contract or 0.0
                # slab1_years = min(years, 5)
                # amount += slab1_years * basic * 1
                # if years > 5:
                #     slab2_years = min(years - 5, 5)
                #     amount += slab2_years * basic * 1.5
                # if years > 10:
                #     completed_years = floor(years - 10)
                #     amount += completed_years * basic * 2
                #
                # rec.kuec_settlement_amount = amount

        # return res
