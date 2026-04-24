# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """
    Extension of the core res.company model to support bilingual company identification
    and signature/stamp configuration. This is useful for official documents that
    require both English and Arabic representations, along with authorized signatures/stamps.

    Additionally, the model links to a specific employee (typically the one authorized
    to sign documents), including their job position and Arabic translations for names
    and titles.
    """

    _inherit = 'res.company'

    company_name = fields.Char(
        string='Company Name in Letters (English)',
        help="The full name of the company written in English letters, "
             "used for official communication and reporting."
    )

    company_name_arabic = fields.Char(
        string='Company Name in Letters (Arabic)',
        help="The full name of the company written in Arabic letters, "
             "used for legal documents and Arabic reports."
    )

    signature = fields.Binary(
        string='Attachment Signature',
        help="Binary field for storing the image of the authorized person's signature "
             "(preferably in PNG or JPG format). Used in reports or PDF documents."
    )

    stamp = fields.Binary(
        string='Attachment Stamp',
        help="Binary field for storing the image of the company stamp or seal "
             "to be used on official PDF reports or other documents."
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help="Select the employee who is authorized to sign or be referenced "
             "in official documents (e.g., contracts, certifications)."
    )

    employee_arabic_name = fields.Char(
        related='employee_id.employee_arabic_name',
        string='Employee (Arabic)',
        help="Arabic name of the selected employee, "
             "used in bilingual reports and contracts."
    )

    job_id = fields.Many2one(
        'hr.job',
        related='employee_id.job_id',
        string='Employee Position',
        help="Job position of the selected employee, "
             "auto-populated from employee record."
    )

    employee_arabic_job_position = fields.Char(
        related='job_id.employee_arabic_job_position',
        string="Employee's Position (Arabic)",
        help="Arabic version of the employee's job "
             "position for use in Arabic documents."
    )
