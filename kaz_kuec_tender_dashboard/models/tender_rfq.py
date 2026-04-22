from odoo import models, api, fields


class TenderRfq(models.Model):
    _inherit = 'tender.rfq'

    @api.model
    def retrieve_dashboard(self):
        """ This function returns the values to populate the custom dashboard in
            the purchase order views.
        """
        self.check_access('read')
        today = fields.Date.today()
        tenders = self.search([]).ids
        Activity = self.env['mail.activity']

        activity_today = Activity.search_count([
            ('res_model', '=', 'tender.rfq'),
            ('res_id', 'in', tenders),
            ('date_deadline', '=', today),
        ])

        activity_due = Activity.search_count([
            ('res_model', '=', 'tender.rfq'),
            ('res_id', 'in', tenders),
            ('date_deadline', '<', today),
        ])

        activity_upcoming = Activity.search_count([
            ('res_model', '=', 'tender.rfq'),
            ('res_id', 'in', tenders),
            ('date_deadline', '>', today),
        ])

        open_tenders = self.search_count([
            ('state', 'in',
             ['draft'])
        ])

        active_tenders = self.search_count([
            ('state', 'in',
             ['active']),
        ])

        under_review_tenders = self.search_count([
            ('state', 'in',
             ['under_review']),
        ])
        awarded_tenders = self.search_count([
            ('state', 'in',
             ['bafo_awarded', 'awarded']),
        ])

        result = {
            'open_tenders': open_tenders,
            'active_tenders': active_tenders,
            'under_review_tenders': under_review_tenders,
            'awarded_tenders': awarded_tenders,
            'activity_today': activity_today,
            'activity_due': activity_due,
            'activity_upcoming': activity_upcoming,
            'company_currency_symbol': self.env.company.currency_id.symbol
        }

        return result



