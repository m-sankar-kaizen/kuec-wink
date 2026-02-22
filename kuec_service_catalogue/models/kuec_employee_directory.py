from odoo import models, fields, api, _

class KuecEmployeeDirectory(models.Model):
    _name = 'kuec.employee.directory'
    _description = 'KUEC Employee Directory'
    _order = 'name'

    active = fields.Boolean(default=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Employee Company',
        required=True,
        domain="[('is_company', '=', True)]",
        ondelete='cascade',
        help="The company/partner this employee works for."
    )
    
    # Personal Info
    name = fields.Char(string='Full Name', required=True)
    full_name_arabic = fields.Char(string='Full Name in Arabic')
    job_title = fields.Char(string='Job Title')
    email = fields.Char(string='Email')
    mobile = fields.Char(string='Mobile Number')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')
    date_of_birth = fields.Date(string='Date of Birth')
    place_of_birth = fields.Char(string='Place of Birth')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed')
    ], string='Marital Status')
    
    # Passport & Nationality
    nationality_id = fields.Many2one('res.country', string='Nationality')
    passport_number = fields.Char(string='Passport Number', copy=False)
    passport_issue_date = fields.Date(string='Passport Issue Date')
    passport_expiry_date = fields.Date(string='Passport Expiry Date')
    passport_place_of_issue = fields.Char(string='Place of Issue')
    
    # UAE Status
    uae_status = fields.Selection([
        ('citizen', 'UAE Citizen'),
        ('resident', 'UAE Resident'),
        ('tourist', 'Tourist / Visitor'),
        ('none', 'No Status (Abroad)')
    ], string='UAE Status', default='none', required=True)
    current_location = fields.Selection([
        ('inside_uae', 'Inside UAE'),
        ('outside_uae', 'Outside UAE')
    ], string='Current Location')
    previous_uae_visa = fields.Boolean(string='Previous UAE Visa', default=False)
    uid_number = fields.Char(string='UID Number')
    emirates_id = fields.Char(string='Emirates ID (EID)', copy=False)
    visa_expiry_date = fields.Date(string='Visa Expiry Date')

    _sql_constraints = [
        ('passport_unique', 'unique(passport_number)', 'Passport number must be unique!'),
        ('emirates_id_unique', 'unique(emirates_id)', 'Emirates ID must be unique!'),
    ]
