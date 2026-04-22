# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrInternshipCertificateWizard(models.TransientModel):
    _name = 'hr.internship.certificate.wizard'
    _description = 'Internship Certificate Generation Wizard'

    internship_id = fields.Many2one('hr.internship', string='Internship', required=True)
    certificate_date = fields.Date(string='Certificate Date', required=True, default=fields.Date.today,
                                  help='Date to appear on the certificate')
    certificate_number = fields.Char(string='Certificate Number', required=True,
                                    help='Unique certificate identification number')
    
    # Display fields from internship
    intern_name = fields.Char(related='internship_id.intern_id.name', string='Intern Name', readonly=True)
    department_name = fields.Char(related='internship_id.department_id.name', string='Department', readonly=True)
    date_start = fields.Date(related='internship_id.date_start', string='Start Date', readonly=True)
    date_end = fields.Date(related='internship_id.date_end', string='End Date', readonly=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super(HrInternshipCertificateWizard, self).default_get(fields_list)
        if 'certificate_number' in fields_list and not res.get('certificate_number'):
            # Generate certificate number
            internship = self.env['hr.internship'].browse(res.get('internship_id'))
            if internship:
                sequence = self.env['ir.sequence'].next_by_code('hr.internship.certificate') or '00000'
                res['certificate_number'] = f"CERT-{internship.name}-{sequence}"
        return res

    def action_generate_certificate(self):
        """Generate the certificate and mark internship"""
        self.ensure_one()
        
        if self.internship_id.state != 'completed':
            raise UserError(_('Certificate can only be generated for completed internships.'))
        
        # Update internship with certificate details
        self.internship_id.write({
            'certificate_generated': True,
            'certificate_date': self.certificate_date,
            'certificate_number': self.certificate_number,
        })
        
        # Generate and return PDF report
        return self.env.ref('hr_internship.action_report_internship_certificate').report_action(self.internship_id)
