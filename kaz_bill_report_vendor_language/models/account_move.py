# -*- coding: utf-8 -*-
from odoo import models, fields, api
from num2words import num2words

# Dictionary mapping currency codes to their Arabic unit/subunit translations
ar_currency_dic = {
    'USD': {'Dollars': 'دولار', 'Cents': 'سنت'},
    'SAR': {'Riyal': 'ريال', 'Halala': 'هلله'},
    'AED': {'Dirham': 'درهم اماراتي', 'Fils': 'فلس'},
    'BHD': {'Dinar': 'دينار بحريني', 'Fils': 'فلس'},
    'EGP': {'Pound': 'جنيه مصري', 'Piastres': 'قرش'},
    'EUR': {'Euros': 'يورو', 'Cents': 'سنت'},
    'KWD': {'Dinar': 'دينار كويتي', 'Fils': 'فلس'},
    'LYD': {'Dinar': 'دينار ليبي', 'Dirham': 'درهم'},
    'MAD': {'Dirham': 'درهم مغربي', 'Centimes': 'سنت'},
    'OMR': {'Rial': 'ريال عماني', 'Baisa': 'بيسا'},
    'QAR': {'Rial': 'ريال قطري', 'Dirham': 'درهم'},
    'RUB': {'Ruble': 'روبيل روسي', 'Kopek': 'كوبيل'},
    'TRY': {'Lira': 'ليره', 'Kurus': 'قرش'},
}


class AccountMove(models.Model):
    """
    Inherits account.move to add:
    - Bank account info (related fields)
    - Amount in words (in both Arabic and English)
    - Custom record naming for journal entries
    """
    _inherit = 'account.move'

    # Bank account related fields (read-only, pulled from res.bank)
    bank_account_id = fields.Many2one('res.bank', string='Bank Account Name')
    bank_name = fields.Char(related='bank_account_id.bank_name', string='Bank Name')
    bank_number = fields.Char(related='bank_account_id.bank_number', string='Bank Number')
    iban_no = fields.Char(related='bank_account_id.iban_no', string='IBAN NO')
    swift_code = fields.Char(related='bank_account_id.swift_code', string='Swift Code')

    # VAT number from the company
    tax_id = fields.Char(string='VAT NO', related='company_id.vat')

    # Computed text representation of amount in words
    text_lang = fields.Char(string='Amount in Words (Lang)', compute='_amount_in_words')
    text_langs = fields.Char(string='Amount in Words (Arabic)', compute='_amount_in_words')

    @api.depends('amount_total')
    def _amount_in_words(self):
        """
        Computes the amount in words (in Arabic and English),
        depending on the user and partner language settings.
        """
        for order in self:
            amount = order.amount_total
            lang = order.env.user.lang
            partner_lang = order.partner_id.lang
            currency = order.currency_id

            text = ''
            ar_text = ''

            # Arabic text for partners with Arabic language setting
            if partner_lang == 'ar_001':
                integer_part = int(str(amount).split('.')[0])
                decimal_part = int(str(amount).split('.')[1])

                ar_text += (
                    num2words(integer_part, lang='ar') + ' ' +
                    ar_currency_dic[currency.name][currency.currency_unit_label] + ' و '
                )
                ar_text += (
                    num2words(decimal_part, lang='ar') + ' ' +
                    ar_currency_dic[currency.name][currency.currency_subunit_label]
                )
                ar_text += ' فقط '

            # English representation based on user language
            if lang == 'en_US':
                integer_part = int(str(amount).split('.')[0])
                decimal_part = int(str(amount).split('.')[1])

                text += currency.currency_unit_label + ' ' + num2words(integer_part, lang='en') + ' '
                text += num2words(decimal_part, lang='en') + ' ' + currency.currency_subunit_label
                text += ' only'

            # Arabic representation for user with Arabic language
            elif lang == 'ar_001':
                integer_part = int(str(amount).split('.')[0])
                decimal_part = int(str(amount).split('.')[1])

                text += (
                    num2words(integer_part, lang='ar') + ' ' +
                    ar_currency_dic[currency.name][currency.currency_unit_label] + ' و '
                )
                text += (
                    num2words(decimal_part, lang='ar') + ' ' +
                    ar_currency_dic[currency.name][currency.currency_subunit_label]
                )

            order.text_lang = text
            order.text_langs = ar_text

    # @api.model_create_multi
    # def create(self, vals_list):
    #     """
    #     Override the create method to auto-generate the name/sequence
    #     based on journal type: 'account.payment' or 'account.move'.
    #     """
    #     for vals in vals_list:
    #         if vals.get('name', 'Draft') == 'Draft':
    #             journal_id = vals.get('journal_id')
    #             if journal_id:
    #                 journal = self.env['account.journal'].browse(journal_id)
    #                 # Choose the appropriate sequence code
    #                 sequence_code = 'account.payment' if journal.type in ('bank', 'cash') else 'account.move'
    #                 # Generate name from the sequence
    #                 vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code) or '/'
    #     return super().create(vals_list)
