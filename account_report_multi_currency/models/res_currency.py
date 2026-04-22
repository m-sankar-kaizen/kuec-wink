# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCurrency(models.Model):
    """
    Extends 'res.currency' to customize the dynamic currency conversion logic
    used in Odoo financial reports.

    - Adds support for custom conversion currency from the report configuration.
    - Overrides `_get_query_currency_table` to build a dynamic SQL VALUES clause,
      mapping each company to a normalized conversion rate and precision.

    This enables:
    - Cross-company currency standardization in analytic and financial reports.
    - Conversion to any selected currency at runtime, per report session.

    Used extensively in multi-company or multi-currency setups where unified
    reporting in a single currency is a business requirement.
    """
    _inherit = 'res.currency'

    @api.model
    def _get_query_currency_table(self, options):
        """
        Constructs a currency mapping table as a PostgreSQL VALUES clause.
        Each row corresponds to:
            - A company ID
            - Conversion rate to the report's selected currency
            - Decimal precision of the currency

        If a report-specific conversion currency is set (`curr_currency_id`),
        it overrides the default user's company currency.

        :param options: Dictionary containing the report context and date
        :return: SQL-compatible VALUES clause for currency conversion
        """
        user_company = self.env.company
        user_currency = user_company.currency_id

        if options.get("report_id"):
            report = self.env['account.report'].browse(options["report_id"])
            if report.curr_currency_id:
                user_currency = report.curr_currency_id

        companies = self.env.companies
        conversion_date = options['date']['date_to']
        currency_rates = self.env['res.currency'].search([])._get_rates(user_company,
                                                                        conversion_date)

        conversion_rates = []
        for company in companies:
            company_currency = company.currency_id
            rate = currency_rates[user_currency.id] / currency_rates[company_currency.id]
            precision = user_currency.decimal_places
            conversion_rates.extend((company.id, rate, precision))

        values_clause = ','.join('(%s, %s, %s)' for _ in companies)
        query = f'(VALUES {values_clause}) AS currency_table(company_id, rate, precision)'

        return self.env.cr.mogrify(query, conversion_rates).decode(self.env.cr.connection.encoding)
