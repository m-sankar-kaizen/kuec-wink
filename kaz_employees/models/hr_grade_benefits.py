from odoo import models, fields, api


class HrGradeBenefit(models.Model):
    """
    Model: hr.grade.benefit
    -------------------------
    Stores aggregated benefit totals for a set of `hr.grade`
     records, grouped via the `grade_benefit_id` field.
    This acts as a report/summary model that computes totals
     of multiple salary components across all linked grades.
    """
    _name = 'hr.grade.benefit'
    _description = 'HR Grade Benefit Summary'

    date = fields.Date(
        string="Computation Date",
        help="Optional date to mark when this benefit summary was computed."
    )

    grade_line_ids = fields.One2many(
        comodel_name='hr.grade',
        inverse_name='grade_benefit_id',
        string='Linked Grades',
        help="List of grades for which totals will be computed."
    )

    total_monthly_personal_allowance = fields.Float(
        string='Total Monthly Personal Allowance',
        compute='compute_total_monthly_personal_allowance'
    )

    total_monthly_premium_uae_allowance = fields.Float(
        string='Total Monthly Premium-UAE Allowance',
        compute='compute_total_monthly_premium_uae_allowance'
    )

    total_monthly_living_allowance = fields.Float(
        string='Total Monthly Living Allowance',
        compute='compute_total_monthly_living_allowance'
    )

    total_monthly_connectivity = fields.Float(
        string='Total Monthly Connectivity Allowance',
        compute='compute_total_monthly_connectivity'
    )

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"Grade Benefit #{record.id}"


    @api.depends('grade_line_ids.monthly_personal_allowance')
    def compute_total_monthly_personal_allowance(self):
        """Computes total of Monthly Personal Allowance from linked grades."""
        for rec in self:
            rec.total_monthly_personal_allowance = sum(
                rec.grade_line_ids.mapped('monthly_personal_allowance'))

    @api.depends('grade_line_ids.monthly_premium_uae_allowance')
    def compute_total_monthly_premium_uae_allowance(self):
        """Computes total of Monthly Premium UAE Allowance from linked grades."""
        for rec in self:
            rec.total_monthly_premium_uae_allowance = sum(
                rec.grade_line_ids.mapped('monthly_premium_uae_allowance'))

    @api.depends('grade_line_ids.monthly_living_allowance')
    def compute_total_monthly_living_allowance(self):
        """Computes total of Monthly Living Allowance from linked grades."""
        for rec in self:
            rec.total_monthly_living_allowance = sum(rec.grade_line_ids.mapped('monthly_living_allowance'))

    @api.depends('grade_line_ids.monthly_connectivity')
    def compute_total_monthly_connectivity(self):
        """Computes total of Monthly Connectivity Allowance from linked grades."""
        for rec in self:
            rec.total_monthly_connectivity = sum(rec.grade_line_ids.mapped('monthly_connectivity'))

    # @api.depends('grade_line_ids.monthly_basic_salary')
    # def compute_total_monthly_basic_salary(self):
    #     for rec in self:
    #         rec.total_monthly_basic_salary = sum(rec.grade_line_ids.mapped('monthly_basic_salary'))

    # @api.depends('grade_line_ids.compa_ratio')
    # def compute_average_compa_ratio(self):
    #     for rec in self:
    #         total = sum(rec.grade_line_ids.mapped('compa_ratio'))
    #         num = len(rec.grade_line_ids.ids)
    #         rec.average_compa_ratio = (total / num) if num > 0 else 0
