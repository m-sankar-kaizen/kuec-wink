from datetime import date, datetime, timedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
class KazCashForecast(models.Model):
    """Concrete forecast line for a specific Forecast Type and Period."""
    _name = 'kaz.cash.forecast'
    _description = "Cash Forecast"
    _inherit = ['mail.thread']
    name = fields.Char('Name')
    company_id = fields.Many2one('res.company', string='Company')
    forecast_type = fields.Selection([('income', 'Cash In'), ('expense', 'Cash OUT'),
                                      ('opening', 'Opening Forecast'), ('net_forecast', 'Net Forecasting'),
                                      ('closing', 'Closing Forecast'),('pending', 'Pending')],
                                     string="Group")
    forecast_value = fields.Float('Forecast Value')
    auto_calculate = fields.Boolean("Auto Calculate", default=True)
    account_ids = fields.Many2many('account.account', string='Account')
    analytic_account_ids = fields.Many2many('account.analytic.account','forecast_analytic_account_id','cash_forecast_id', string="Analytic Accounts", copy=False)
    real_value = fields.Float('Real Value')
    difference_value = fields.Float('Difference Value',compute='_compute_difference')
    forecast_date = fields.Date('Forecast Date')
    forecast_period_id = fields.Many2one('cash.forecast.fiscal.period', string='Forecast Period')
    forecast_type_id = fields.Many2one('kaz.cash.forecast.type', string='Forecast Type')
    cash_forecast_category_id = fields.Many2one('kaz.cash.forecast.categories', string="Categories Name")
    forecast_property = fields.Selection([('over', 'Over Forecast'),
                                          ('under', 'Under Forecast'),
                                          ('true', 'True Value')], compute='_compute_difference', string="Forecast Property", readonly=True)
    dep_forecast_ids = fields.Many2many('kaz.cash.forecast.type', 'cash_forecast_dependent_rel',
                                        string='Dependant Forecast Type')
    @api.model
    def create(self, vals):
        period_id = vals.get('forecast_period_id')
        if period_id:
            period = self.env['cash.forecast.fiscal.period'].browse(period_id)
            if period.is_locked:
                raise ValidationError(_("This fiscal period is locked; you cannot create forecasts for it."))
        return super().create(vals)

    def write(self, vals):
        # Determine the effective period for each record (before/after write)
        for rec in self:
            period_id = vals.get('forecast_period_id') or rec.forecast_period_id.id
            period = self.env['cash.forecast.fiscal.period'].browse(period_id)
            if period.is_locked:
                raise ValidationError(_("This fiscal period is locked; you cannot modify forecasts for it."))
        return super().write(vals)
    def unlink(self):
        for rec in self:
            if rec.forecast_period_id.is_locked:
                raise ValidationError(_("This fiscal period is locked; you cannot delete forecasts for it."))
        return super().unlink()
    def _compute_difference(self):
        """Compute variance and qualitative property for past/current period forecasts only."""
        for frc in self:
            if frc.forecast_value and frc.forecast_period_id and frc.forecast_period_id.start_date < date.today():
                difference_value = frc.real_value - frc.forecast_value
                if (difference_value > 0 and frc.forecast_type == 'income') or \
                        (difference_value < 0 and frc.forecast_type == 'expense'):
                    forecast_property = 'under'
                elif (difference_value < 0 and frc.forecast_type in ['income', 'opening', 'closing']) or \
                        (difference_value > 0 and frc.forecast_type == 'expense'):
                    forecast_property = 'over'
                else:
                    forecast_property = 'true'
                frc.difference_value = difference_value
                frc.forecast_property = forecast_property
            else:
                frc.difference_value = 0
                frc.forecast_property = ''

    @api.constrains('account_ids', 'forecast_period_id', 'forecast_type_id')
    def _check_unique(self):
        """Avoid duplicates for same type/period/account set."""
        if duplicate_records := self.search([('id', '!=', self.id), ('account_ids', 'in', self.account_ids.ids),
                                             ('forecast_period_id', '=', self.forecast_period_id.id),
                                             ('forecast_type_id', '=', self.forecast_type_id.id)]):
            raise ValidationError(_('Forecast data not unique.'))

    def _get_opening_balance(self, forecast_type_id, forecast_period_id):
        """Opening balance rolls from previous period's closing if exists, otherwise
                compute using account_move_line balance before period start (SQL used for performance)."""

        prev_period_id = self.env['cash.forecast.fiscal.period'].search(
            [('company_id', '=', forecast_period_id.company_id.id), ('end_date', '=', forecast_period_id.start_date - timedelta(days=1))])
        if previous_cash_forecast := self.env['kaz.cash.forecast'].search(
                [('forecast_type', '=', 'closing'), ('forecast_period_id', '=', prev_period_id.id)], limit=1):
            return previous_cash_forecast.real_value
        query = """select
                        sum(debit)-sum(credit) as balance
                    from
                        account_move_line
                    where
                        date < '{}' and account_id {} {} 
                """.format(forecast_period_id.start_date, 'in' if len(forecast_type_id.account_ids.ids) > 1 else '=',
                           tuple(forecast_type_id.account_ids.ids) if len(
                               forecast_type_id.account_ids.ids) > 1 else forecast_type_id.account_ids.id)
        self._cr.execute(query)
        return self._cr.fetchall()[0][0]
    def get_forecast_type_real_value(self):
        """Compute 'real_value' for this record based on its Forecast Type definition."""
        forecast_type_id = self.forecast_type_id
        forecast_period_id = self.forecast_period_id
        start_date = datetime.combine(forecast_period_id.start_date, datetime.min.time())
        end_date = datetime.combine(forecast_period_id.end_date, datetime.max.time())
        real_values = 0
        if forecast_type_id.type == 'opening':
            real_values = self._get_opening_balance(forecast_type_id, forecast_period_id)
        elif forecast_type_id.type in ['closing', 'net_forecast']:
            current_period_forecasts = self.env['kaz.cash.forecast'].search(
                [('forecast_period_id', '=', forecast_period_id.id)])
            opening_forecast_id = current_period_forecasts.filtered(lambda frc: frc.forecast_type == 'opening')
            period_income_forecast_ids = current_period_forecasts.filtered(lambda frc: frc.forecast_type == 'income')
            period_expense_forecast_ids = current_period_forecasts.filtered(lambda frc: frc.forecast_type == 'expense')
            period_income = sum(
                period_income_forecast_ids.mapped('real_value')) if period_income_forecast_ids else 0
            period_expense = sum(
                period_expense_forecast_ids.mapped('real_value')) if period_expense_forecast_ids else 0
            real_values = (opening_forecast_id.real_value \
                if forecast_type_id.type == 'closing' else 0) + period_income - period_expense
        elif move_line := self.env['account.move.line'].search(
                [('company_id', '=', self.company_id.id), ('move_id.state', 'not in', ['draft', 'cancel']),
                 ('date', '>=', start_date), ('date', '<=', end_date), ('account_id', 'in', self.account_ids.ids)]):
            liability_line = move_line.filtered(lambda line: line.account_id.internal_group in ['liability'])
            liability_amount = sum(liability_line.mapped('credit')) - sum(liability_line.mapped('debit'))
            asset_line = move_line.filtered(lambda line: line.account_id.internal_group in ['asset'])
            asset_amount = sum(asset_line.mapped('debit')) - sum(asset_line.mapped('credit'))
            credited_line = move_line.filtered(lambda line: line.account_id.internal_group in ['income'])
            credited_amount = sum(credited_line.mapped('credit')) - sum(credited_line.mapped('debit'))
            debited_line = move_line.filtered(lambda line: line.account_id.internal_group in ['expense'])
            debited_amount = sum(debited_line.mapped('debit')) - sum(debited_line.mapped('credit'))
            real_values = liability_amount + credited_amount + debited_amount + asset_amount
        if forecast_type_id.auto_calculate and forecast_type_id.calculate_from == 'past_account_entries' \
                    and self.forecast_type not in ['opening', 'net_forecast', 'closing'] \
                    and forecast_type_id.real_value_multiply_by:
            real_values *= forecast_type_id.real_value_multiply_by
        return real_values
    def get_real_values(self, period_id=False):
        """Skip locked periods to avoid accidental changes or cron failures."""
        if period_id:
            period = self.env['cash.forecast.fiscal.period'].browse(period_id)
            if period.is_locked:
                # Nothing to do if it's locked
                return True
            forecast_records = self.search([('forecast_period_id.start_date', '<=', period.end_date),
                                            ('forecast_period_id.is_locked', '=', False)])
        else:
            forecast_records = self.search([
                ('forecast_period_id.end_date', '<=', date.today()),
                ('real_value', '=', False),
                ('forecast_period_id.is_locked', '=', False),
            ])

        period_ids = forecast_records.mapped('forecast_period_id')
        for per in period_ids:
            for rec in forecast_records.filtered(lambda r: r.forecast_period_id.id == per.id
                                                 ).sorted(lambda r: r.forecast_type_id.sequence):
                real_value = rec.get_forecast_type_real_value()
                rec.real_value = real_value
        return True