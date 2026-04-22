# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Subina P (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import models


class Cashflow(models.Model):
    """ Class for getting report data """
    _name = "cashflow"
    _description = 'Report advanced cash flows'

    def get_report_values(self, data=None):
        """
          Fetches and returns the report values for the cashflow report.
          :param data: Dictionary containing parameters for fetching the report data.
          :return: Dictionary containing fetched data, journal results, and account results.
              """
        account_res = []
        # Query to fetch all data without date filtration
        # Note: The original 'fetched_data' query was unused in the frontend/logic, so it is removed.
        
        # Optimization: Only search accounts that have move lines in posted state to avoid iterating all accounts?
        # However, to preserve exact behavior (iterating all accounts), we keep the loop but we could optimize.
        # For now, we keep the loop structure but use ORM for data fetching.
        
        accounts = self.env['account.account'].search([])
        for account in accounts:
            child_lines = self._get_lines(account, data)
            if child_lines:
                account_res.append(child_lines)
        return {
            'fetched_data': [], # Unused but kept for structure compatibility if needed
            'journal_res': [],
            'account_res': account_res,
        }

    def _get_lines(self, account, data):
        """ fetch values for lines"""
        # Fetch move lines for this account where move is posted
        domain = [
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'posted')
        ]
        
        # 1. Fetch individual move lines details
        # Using search_read is slightly less efficient for huge data than pure SQL but safer.
        # We need: aml.id, aml.move_id, aml.account_id, aj.name, am.name, debit, credit
        
        move_lines_recs = self.env['account.move.line'].search(domain)
        
        if not move_lines_recs:
             return None

        fetched_data = []
        for line in move_lines_recs:
             fetched_data.append({
                 'id': line.id,
                 'move_id': line.move_id.id,
                 'account_id': line.account_id.id,
                 'name': line.journal_id.name,
                 'move_name': line.move_id.name,
                 'total_debit': line.debit,
                 'total_credit': line.credit,
             })

        # 2. Fetch journal grouped totals
        # Group by journal_id
        
        journal_lines = []
        # Odoo 18 _read_group
        results = self.env['account.move.line']._read_group(
            domain=domain,
            groupby=['journal_id'],
            aggregates=['debit:sum', 'credit:sum']
        )
        
        for journal, total_debit, total_credit in results:
            journal_lines.append({
                'account_name': account.name, # Was aa.name
                'id': journal.id,
                'name': journal.name,
                'total_debit': total_debit,
                'total_credit': total_credit,
            })

        if fetched_data:
            return {
                'account': account.name,
                'code': account.code,
                'move_lines': fetched_data,
                'journal_lines': journal_lines,
            }
