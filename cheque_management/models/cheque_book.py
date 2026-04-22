# -*- coding: utf-8 -*-
""" Cheque Book """
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ChequeBook(models.Model):
    """ Cheque Book """
    _name = 'cheque.book'
    _description = 'Cheque Book'

    name = fields.Char()
    start = fields.Char()
    end = fields.Char()
    next_page = fields.Char()
    is_finished = fields.Boolean()

    @api.model
    def create(self, vals):
        """ Override create() """
        res = super(ChequeBook, self).create(vals)
        res.next_page = res.start
        return res

    @api.constrains('start', 'end')
    def _check_start_and_end(self):
        """ Validate start_and_end """

        if self.start.isdigit() <= 0:
            raise ValidationError(
                _("The start page must be greater than zero"))
        if  not self.start.isdigit():
            raise ValidationError(
                _('Start must be number'))
        if self.end.isdigit() <= 0:
            raise ValidationError(
                _("The end page must be greater than zero"))
        if  not self.start.isdigit():
            raise ValidationError(
                _('End must be number'))










