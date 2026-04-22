# -*- coding: utf-8 -*-
import logging
import base64

from odoo.http import Controller, route, request, Response
from odoo import Command, fields

_logger = logging.getLogger(__name__)


class VendorManagement(Controller):

    @route(['/web/get-attachment/<string:company_type>'], type='json', auth="public", website=True)
    def get_attachment_lines(self, company_type):
        website = request.website
        company_id = website.company_id.id if website and website.company_id else request.env.company.id
        domain = [('company_type', '=', company_type), ('is_vendor', '=', True),
                  ('company_id', '=', company_id)]
        attachment_lines = request.env['attachment.attachment'].sudo().search(domain).mapped(
            'checklist_line_ids')
        attachment_lines = attachment_lines.sudo().read(
            ['id', 'name', 'attachment_is_required', 'expiry_date_required', 'sequence',
             'attachment_type']
        )
        return attachment_lines

    def _get_vendor_signup_values(self, **kw):
        website = request.website
        company_id = website.company_id if website and website.company_id else request.env.company
        company_domain = [('company_id', '=', company_id.id)]

        country = request.env['res.country'].sudo().search_fetch(
            domain=[],
            field_names=['id', 'name'],
            order='name asc',
        )
        partner_category = request.env['partner.category'].sudo().search_fetch(
            domain=company_domain,
            field_names=['id', 'name'],
            order='name asc',
        )
        company_size = request.env['company.size'].sudo().search_fetch(
            domain=company_domain,
            field_names=['id', 'name'],
            order='sequence asc',
        )
        iso_certification = request.env['iso.certification'].sudo().search_fetch(
            domain=company_domain,
            field_names=['id', 'name'],
            order='name asc',
        )
        currency = request.env['res.currency'].sudo().search_fetch(
            domain=[],
            field_names=['id', 'name', 'symbol'],
            order='name asc',
        )
        products = request.env['product.template'].sudo().search_fetch(
            domain=company_domain + [('purchase_ok', '=', True),
                                     ('is_available_for_vendor_portal', '=', True)],
            field_names=['id', 'name', 'default_code'],
            order='name asc',
        )
        bank_ids = request.env['res.bank'].sudo().search_fetch(
            domain=[],
            field_names=['id', 'name', 'bic'],
            order='name asc',
        )
        return {
            'country': country,
            'partner_category': partner_category,
            'company_size': company_size,
            'iso_certification': iso_certification,
            'currency': currency,
            'products': products,
            'bank_ids': bank_ids,
            'company_id': company_id,
            'is_public': request.env.user._is_public(),
        }

    @route(['/vendor/signup'], type='http', auth="public", website=True)
    def vendor_signup(self, **kw):
        values = self._get_vendor_signup_values(**kw)
        error_message = request.session.pop('vendor_error', None)

        if error_message:
            values['error_message'] = error_message

        return request.render('kaz_vendor_management.vendor_signup', values)

    @route(['/vendor/register'], type='http', auth="public", website=True)
    def vendor_register(self, **kw):
        _logger.debug(f"Vendor register request with {kw}")
        company_type = kw.get('company_type')
        phone = kw.get('phone')
        mobile = kw.get('mobile')
        email = kw.get('email')
        website = request.website
        company_id = website.company_id if website and website.company_id else request.env.company
        _logger.info(f"Position 1")
        # otp = kw.get('otp')
        # response = self.verify_vendor_otp(email, otp)
        # if response.get('status') == 'failed':
        #     _logger.info("OTP verification failed")
        #     request.session['vendor_error'] = "OTP verification failed, Please try again"
        #     return request.redirect('/vendor/signup')
        # ####The above validation is removed as the session is not persistent
        if not phone and not mobile:
            _logger.info("Vendor register request without phone or mobile")
            request.session[
                'vendor_error'] = "Please provide either phone or mobile, Please try again"
            return request.redirect('/vendor/signup')

        _logger.info(f"Position 2")

        existing_partner = request.env['res.partner'].sudo().search(
            [('email', '=', email)])  # Add Company?
        if existing_partner:
            _logger.info(f"The email: {email} is already registered")
            request.session['vendor_error'] = f"The email: {email} is already registered."
            return request.redirect('/vendor/signup')

        _logger.info(f"Position 3")

        attachments = {}
        for key in request.httprequest.files:
            attachments[key] = request.httprequest.files[key]

        # Handle links from form submission
        attachment_links = {}
        for k, v in kw.items():
            if k.startswith('attach_link_'):
                attachment_links[k] = v

        _logger.info(f"Position 4")

        # Handle expiry dates
        expiry_dates = {}
        for k, v in kw.items():
            if k.startswith('expiry_'):
                expiry_dates[k] = v

        _logger.info(f"Position 4")

        addition_partner_values = {
            "contact_name": kw.get('contact_name'),
            "contact_function": kw.get('contact_function'),
            "contact_email": kw.get('contact_email'),
            "contact_phone": kw.get('contact_phone'),
        }

        _logger.info(f"Position 5")

        has_worked_for_govt = kw.get('has_worked_for_govt') == 'on'
        vendor_values = {
            "is_portal": True,
            "is_vendor": True,
            "company_id": company_id.id,
            "street": kw.get('street'),
            "street2": kw.get('street2'),
            "city": kw.get('city'),
            "zip": kw.get('zip'),
            "website": kw.get('website'),
            "icv_score": kw.get('icv_score', 0),
            "phone": phone,
            "mobile": mobile,
            "has_worked_for_govt": has_worked_for_govt,
            "company_type": company_type,
            "name": kw.get('name'),
            "years_of_experience": kw.get('years_of_experience'),
            "email": email,
            "delivery_capacity": kw.get('delivery_capacity'),
            "vat": kw.get('vat'),
            # "property_purchase_currency_id": int(kw.get('property_purchase_currency_id')),
            "country_id": int(kw.get('country_id')),
            "state_id": int(kw.get('state_id')),
            "company_size_id": int(kw.get('company_size_id')),
        }
        purchase_currency_id = int(kw.get('property_purchase_currency_id', 0))

        _logger.info(f"Position 6")
        iso_certification_ids = request.httprequest.form.getlist('iso_certification_ids')
        partner_category_ids = request.httprequest.form.getlist('partner_category_ids')
        offered_product_ids = request.httprequest.form.getlist('products_ids')
        companies_worked_for = request.httprequest.form.getlist('companies_worked_for')

        _logger.info(f"Position 7")

        if iso_certification_ids:
            int_ids = [int(id_str) for id_str in iso_certification_ids]
            vendor_values['iso_certification_ids'] = [Command.set(int_ids)]
        if partner_category_ids:
            int_ids = [int(id_str) for id_str in partner_category_ids]
            vendor_values['partner_category_ids'] = [Command.set(int_ids)]
        if offered_product_ids:
            int_ids = [int(id_str) for id_str in offered_product_ids]
            vendor_values['offered_product_ids'] = [Command.set(int_ids)]

        if companies_worked_for and has_worked_for_govt:
            vendor_values['worked_company_ids'] = [Command.create({
                'sequence': idx + 1,
                'name': name,
            }) for idx, name in enumerate(companies_worked_for)]

        _logger.info(f"Position 8")

        other_pc = kw.get('other_pc') == 'on'
        other_certificates = kw.get('other_certificates') == 'on'
        other_op = kw.get('other_op') == 'on'
        other_partner_category = kw.get('other_partner_category')
        other_partner_certificates = kw.get('other_partner_certificates')
        other_offered_product = kw.get('other_offered_product')

        _logger.info(f"Position 9")

        if other_certificates and other_partner_certificates:
            vendor_values['other_partner_certificates'] = other_partner_certificates

        if other_pc and other_partner_category:
            vendor_values['other_partner_category'] = other_partner_category

        if not partner_category_ids and not other_partner_category:
            _logger.info("Type of Business is a required field")
            request.session['vendor_error'] = "Type of Business is a required field"
            return request.redirect('/vendor/signup')

        _logger.info(f"Position 10")

        if other_op and other_offered_product:
            vendor_values['other_offered_product'] = other_offered_product

        if attachments.get('image_1920'):
            image_file = attachments['image_1920']
            image_base64 = base64.b64encode(image_file.read())
            vendor_values['image_1920'] = image_base64

        attachment_lines = self.get_attachment_lines(company_type)

        _logger.info(f"Position 11")

        if attachment_lines:
            attach = []
            for idx, attachment in enumerate(attachment_lines):
                line_id = attachment.get('id')
                attachment_type = attachment.get('attachment_type')
                attachment_is_required = attachment.get('attachment_is_required')
                expiry_date_required = attachment.get('expiry_date_required')
                attachment_link = attachment_links.get(f"attach_link_{line_id}")
                expiry_date = expiry_dates.get(f"expiry_{line_id}")
                attach_file = attachments.get(f"attach_file_{line_id}")

                if attachment_is_required:
                    if attachment_type == 'link':
                        if not attachment_link:
                            request.session[
                                'vendor_error'] = "One or more of the attachment links is Missing, Please retry"
                            request.redirect("/vendor/signup")
                    else:
                        if not attach_file:
                            request.session[
                                'vendor_error'] = "One or more of the attachment file is Missing, Please retry"
                            request.redirect("/vendor/signup")
                if expiry_date_required:
                    if not expiry_date:
                        request.session[
                            'vendor_error'] = "One or more of the attachment expiry is Missing, Please retry"
                        return request.redirect("/vendor/signup")
                    expiry_date_obj = fields.Date.from_string(expiry_date)
                    if expiry_date_obj <= fields.Date.today():
                        request.session[
                            'vendor_error'] = "One or more of the attachment expiry is Today or already expired, Please retry"
                        return request.redirect("/vendor/signup")

                line_create_values = {
                    'sequence': idx + 1,
                    'name': attachment.get('name'),
                    'attachment_is_required': attachment_is_required,
                    'expiry_date_required': expiry_date_required,
                    'attachment_type': attachment_type,
                    'attachment_link': attachment_link,
                    'expiry_date': expiry_date,
                }
                if attach_file:
                    file_content = attach_file.read()
                    encoded_content = base64.b64encode(file_content)
                    ir_attachment = request.env['ir.attachment'].sudo().create({
                        'name': attach_file.filename,
                        'datas': encoded_content,
                        'mimetype': attach_file.mimetype,
                        'res_model': 'partner.attachment.line',
                    })
                    line_create_values['ir_attachment_ids'] = [Command.link(ir_attachment.id)]
                attach.append(Command.create(line_create_values))
            vendor_values['partner_attachment_line_ids'] = attach

            _logger.info(f"Position 12")
            if company_type == 'company':
                vendor_values.update(addition_partner_values)

            bank_currency_ids = request.httprequest.form.getlist('bank_currency_ids')
            acc_numbers = request.httprequest.form.getlist('acc_numbers')
            bank_ids = request.httprequest.form.getlist('bank_ids')
            bank_names = request.httprequest.form.getlist('bank_name')

            bank_create_vals = []
            has_valid_bank = False

            _logger.info(f"Position 13")

            for i in range(len(acc_numbers)):
                acc_number = acc_numbers[i].strip()
                currency_id = bank_currency_ids[i].strip() if i < len(bank_currency_ids) else "0"
                bank_id = bank_ids[i].strip() if i < len(bank_ids) else "0"
                bank_name = bank_names[i].strip() if i < len(bank_names) else ""

                # Skip row only if currency or account number is missing
                if not acc_number or currency_id == "0":
                    # If the first row, raise error
                    request.session['vendor_error'] = (
                        "Bank Account Number and Currency are required. Please try again."
                    )
                    return request.redirect("/vendor/signup")

                has_valid_bank = True
                vals = {
                    'acc_number': acc_number,
                    'currency_id': int(currency_id),
                    'portal_bank_name': bank_name,
                }
                if bank_id != "0":
                    vals['bank_id'] = int(bank_id)

                bank_create_vals.append(Command.create(vals))

            if not has_valid_bank:
                request.session['vendor_error'] = (
                    "At least one Bank Account with valid Currency is required. Please try again."
                )
                return request.redirect("/vendor/signup")

            _logger.info(f"Position 14")

            vendor_values['bank_ids'] = bank_create_vals
        _logger.info(f"Vendor tobe created 123 ---")
        vendor = request.env['res.partner'].sudo().create(vendor_values)
        _logger.info(f"Vendor created 123")
        # Write company-dependent field separately under explicit sudo
        if purchase_currency_id:
            _logger.info(f"Vendor to write 123")
            vendor.sudo().write({'property_purchase_currency_id': purchase_currency_id})
            _logger.info(f"Vendor write 123")

        _logger.info(f"Vendor created going to send mail, record id: {vendor.id}, vendor name: {vendor.name}")
        vendor.sudo()._create_activity_and_send_registration_success_mail()
        _logger.info(
            f"Vendor created successfully, record id: {vendor.id}, vendor name: {vendor.name}")

        return request.redirect('/vendor/register/success')

    @route(['/vendor/register/success'], type='http', auth="public", website=True)
    def vendor_register_success(self, **kw):
        _logger.info(f"Position success - 1")
        return request.render('kaz_vendor_management.vendor_register_successful')

    @route(['/web/get-state/<int:rec_id>'], type='json', auth="public")
    def get_state(self, rec_id, **kw):
        states = request.env['res.country.state'].sudo().search_read(
            domain=[('country_id', '=', rec_id)],
            fields=['name'],
            order='name asc',
        )
        return states

    @route('/vendor/send_otp', type='json', auth='public', methods=['POST'])
    def send_vendor_otp(self, email, name="", **kwargs):
        try:
            vendor_otp = request.env['vendor.otp'].sudo().create({'email': email, 'name': name})

            template = request.env.ref('kaz_vendor_management.email_template_vendor_otp')
            email_values = {'email_to': email}
            template.sudo().with_context().send_mail(
                vendor_otp.id,
                force_send=True,
                email_values=email_values
            )
        except Exception as e:
            _logger.error(e)
            return {'status': 'failed', 'message': str(e)}
        return {'status': 'success', 'message': 'OTP sent successfully'}

    @route('/vendor/verify_otp', type='json', auth='public', methods=['POST'])
    def verify_vendor_otp(self, email, otp, **kwargs):
        otp_record = request.env['vendor.otp'].sudo().search([('email', '=', email)],
                                                             order='id desc', limit=1)
        if not otp_record:
            return {'status': 'failed', 'message': "No OTP found for this email."}
        if not otp_record.is_valid():
            return {'status': 'failed', 'message': "OTP expired."}
        if otp_record.otp != otp:
            return {'status': 'failed', 'message': "Incorrect OTP."}
        return {'status': 'success', 'message': "OTP verified."}
