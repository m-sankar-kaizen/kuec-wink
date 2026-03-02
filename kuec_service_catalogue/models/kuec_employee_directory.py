from odoo import models, fields, api, exceptions, _

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

    # NOTE: We intentionally do NOT use _sql_constraints for passport_number and emirates_id
    # because PostgreSQL treats '' (empty string) as a value, so two records with no passport
    # number would violate a standard UNIQUE constraint. Instead we use @api.constrains
    # which skips the check when the field is blank/False.

    @api.constrains('passport_number')
    def _check_passport_unique(self):
        for rec in self:
            if not rec.passport_number:
                continue
            duplicate = self.search([
                ('passport_number', '=', rec.passport_number),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise exceptions.ValidationError(
                    _('Passport number "%s" is already used by another employee.') % rec.passport_number
                )

    @api.constrains('emirates_id')
    def _check_emirates_id_unique(self):
        for rec in self:
            if not rec.emirates_id:
                continue
            duplicate = self.search([
                ('emirates_id', '=', rec.emirates_id),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise exceptions.ValidationError(
                    _('Emirates ID "%s" is already used by another employee.') % rec.emirates_id
                )

    @api.model_create_multi
    def create(self, vals_list):
        # Convert empty strings to False so the uniqueness check above works correctly
        for vals in vals_list:
            if vals.get('passport_number') == '':
                vals['passport_number'] = False
            if vals.get('emirates_id') == '':
                vals['emirates_id'] = False
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('passport_number') == '':
            vals['passport_number'] = False
        if vals.get('emirates_id') == '':
            vals['emirates_id'] = False
        return super().write(vals)

    # ISSUE-001: Empty-string normalization moved to post_init_hook (ORM only; no raw SQL).
