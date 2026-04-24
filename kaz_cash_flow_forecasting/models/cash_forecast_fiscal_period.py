from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class CashForecastFiscalPeriod(models.Model):
    """Atomic forecasting window (day/week/month) within a Fiscal Year."""
    _name = 'cash.forecast.fiscal.period'
    _description = "Cash forecast Fiscal Period"
    _rec_name = 'code'
    _order = 'start_date'
    code = fields.Char("Code")
    fiscal_id = fields.Many2one("cash.forecast.fiscal.year", "Fiscal Year", ondelete='cascade')
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    company_id = fields.Many2one('res.company', string='Company', related='fiscal_id.company_id')
    period_interval = fields.Selection(
        string='Period Interval',
        selection=[('days', 'Daily'),
                   ('weeks', 'Weekly'),
                   ('months', 'Monthly')],
        related='fiscal_id.period_interval')
    is_locked = fields.Boolean(
        string="Locked",
        help="When enabled, this period is frozen: no create/edit/delete on related cash forecasts."
    )

    def action_lock_period(self):
        self.ensure_one()
        self.is_locked = True
        return True

    def action_unlock_period(self):
        self.ensure_one()
        self.is_locked = False
        return True
    def update_cash_forecast(self):
        """Open the wizard prefilled for this period."""
        return self.env['create.update.cash.forecast'].with_context(period_id=self.id).update_cash_forecast()
    @api.constrains('start_date', 'end_date')
    def _check_period_date(self):
        if self.search([('id', '!=', self.id), '|', ('start_date', '=', self.start_date),
                        ('end_date', '=', self.end_date), ('company_id', '=', self.company_id.id)]):
            raise ValidationError(_("This date period is already created"))
        return True
    def unlink(self):
        if self.env['kaz.cash.forecast'].search([('forecast_period_id', 'in', self.ids)]):
            raise ValidationError(_("You can't Delete period Because This Period Forecast already created"))
        return super(CashForecastFiscalPeriod, self).unlink()