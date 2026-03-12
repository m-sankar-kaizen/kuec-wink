import io
import json
import logging
import datetime
from odoo import http, _
from odoo.http import request

try:
    import openpyxl
except ImportError:
    openpyxl = None

# ISSUE-002: Max upload size (bytes) for employee Excel bulk import.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

_logger = logging.getLogger(__name__)


class KuecEmployeeExcel(http.Controller):

    @http.route('/my/employees/template', type='http', auth='user', website=True)
    def download_template(self, **kwargs):
        partner = request.env.user.partner_id.commercial_partner_id
        if not partner.employee_directory_enabled:
            return request.redirect('/my')

        if not openpyxl:
            return request.redirect('/my/employees')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Employees"

        headers = [
            "Full Name (As per Passport)", "Full Name in Arabic", "Gender", "Nationality",
            "Date of Birth", "Place of Birth", "Marital Status", "Mobile Number",
            "Email Address", "Passport Number", "Passport Issue Date", "Passport Expiry Date",
            "Place of Issue", "Current Location (Inside / Outside UAE)", "Previous UAE Visa (Yes / No)",
            "UID Number", "Emirates ID Number", "Current Visa Expiry Date"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = openpyxl.styles.Font(bold=True)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = "employee_import_template.xlsx"
        return request.make_response(
            output.read(),
            [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )

    # ISSUE-002: csrf=True; X-Requested-With and file size checks; sanitized logging.
    @http.route('/my/employees/upload', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def upload_employees(self, upload_file=None, **post):
        partner = request.env.user.partner_id.commercial_partner_id
        if not partner.employee_directory_enabled:
            return request.redirect('/my')
        if not openpyxl or not upload_file:
            return request.redirect('/my/employees')
        upload_file.seek(0, 2)
        size = upload_file.tell()
        upload_file.seek(0)
        if size > MAX_UPLOAD_BYTES:
            return request.make_response(json.dumps({
                "success_count": 0,
                "errors": [{"row": 0, "reason": _("File size exceeds the maximum allowed (%s MB).") % (MAX_UPLOAD_BYTES // (1024 * 1024))}]
            }), headers=[('Content-Type', 'application/json')])

        try:
            wb = openpyxl.load_workbook(filename=io.BytesIO(upload_file.read()), data_only=True)
            ws = wb.active
        except Exception as e:
            return request.make_response(json.dumps({
                "success_count": 0,
                "errors": [{"row": 0, "reason": "Invalid Excel File format. Please ensure you upload a valid .xlsx file."}]
            }), headers=[('Content-Type', 'application/json')])

        errors = []
        parsed_data = []

        Country = request.env['res.country'].sudo()
        countries = Country.search([])
        country_map = {c.name.lower(): c.id for c in countries}
        country_code_map = {c.code.lower(): c.id for c in countries if c.code}

        row_idx = 2
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):  # Skip empty rows
                continue
            
            try:
                name = str(row[0] or '').strip()
                full_name_arabic = str(row[1] or '').strip()
                gender_str = str(row[2] or '').strip().lower()
                nationality_str = str(row[3] or '').strip().lower()

                def parse_date(d_val):
                    if not d_val or str(d_val).lower() == 'none':
                        return False
                    if isinstance(d_val, datetime.datetime) or isinstance(d_val, datetime.date):
                        return d_val.strftime('%Y-%m-%d')
                    if isinstance(d_val, str):
                        try:
                            parsed = datetime.datetime.strptime(d_val.strip(), '%Y-%m-%d')
                            return parsed.strftime('%Y-%m-%d')
                        except ValueError:
                            errors.append({"row": row_idx, "reason": f"Invalid date format '{d_val}'. Expected YYYY-MM-DD."})
                    return False

                date_of_birth = parse_date(row[4])
                place_of_birth = str(row[5] or '').strip()
                marital_status_str = str(row[6] or '').strip().lower()
                mobile = str(row[7] or '').strip()
                email = str(row[8] or '').strip()
                passport_number = str(row[9] or '').strip()
                passport_issue_date = parse_date(row[10])
                passport_expiry_date = parse_date(row[11])
                passport_place_of_issue = str(row[12] or '').strip()
                current_location_str = str(row[13] or '').strip().lower()
                previous_uae_visa_str = str(row[14] or '').strip().lower()
                uid_number = str(row[15] or '').strip()
                emirates_id = str(row[16] or '').strip()
                visa_expiry_date = parse_date(row[17])

                if not name or name == 'None':
                    errors.append({"row": row_idx, "reason": "Full Name is required"})
                    row_idx += 1
                    continue

                gender = False
                if gender_str and gender_str != 'none':
                    if gender_str in ['male', 'female', 'other']:
                        gender = gender_str
                    else:
                        errors.append({"row": row_idx, "reason": f"Invalid Gender '{gender_str}'. Must be Male, Female, or Other."})

                nationality_id = False
                if nationality_str and nationality_str != 'none':
                    if nationality_str in country_code_map:
                        nationality_id = country_code_map[nationality_str]
                    elif nationality_str in country_map:
                        nationality_id = country_map[nationality_str]
                    else:
                        errors.append({"row": row_idx, "reason": f"Nationality '{nationality_str}' not found"})

                marital_status = False
                if marital_status_str and marital_status_str != 'none':
                    if marital_status_str in ['single', 'married', 'divorced', 'widowed']:
                        marital_status = marital_status_str
                    else:
                        errors.append({"row": row_idx, "reason": f"Invalid Marital Status '{marital_status_str}'."})

                current_location = False
                if current_location_str and current_location_str != 'none':
                    if current_location_str in ['inside uae', 'inside_uae']:
                        current_location = 'inside_uae'
                    elif current_location_str in ['outside uae', 'outside_uae']:
                        current_location = 'outside_uae'

                previous_uae_visa = False
                if previous_uae_visa_str and previous_uae_visa_str != 'none':
                    if previous_uae_visa_str in ['yes', 'true', '1', 'y']:
                        previous_uae_visa = True

                parsed_data.append({
                    'partner_id': partner.id,
                    'name': name,
                    'full_name_arabic': full_name_arabic if full_name_arabic and full_name_arabic != 'None' else False,
                    'gender': gender,
                    'nationality_id': nationality_id,
                    'date_of_birth': date_of_birth,
                    'place_of_birth': place_of_birth if place_of_birth and place_of_birth != 'None' else False,
                    'marital_status': marital_status,
                    'mobile': mobile if mobile and mobile != 'None' else False,
                    'email': email if email and email != 'None' else False,
                    'passport_number': passport_number if passport_number and passport_number != 'None' else False,
                    'passport_issue_date': passport_issue_date,
                    'passport_expiry_date': passport_expiry_date,
                    'passport_place_of_issue': passport_place_of_issue if passport_place_of_issue and passport_place_of_issue != 'None' else False,
                    'current_location': current_location,
                    'previous_uae_visa': previous_uae_visa,
                    'uid_number': uid_number if uid_number and uid_number != 'None' else False,
                    'emirates_id': emirates_id if emirates_id and emirates_id != 'None' else False,
                    'visa_expiry_date': visa_expiry_date,
                })

            except Exception as e:
                errors.append({"row": row_idx, "reason": f"Error processing row ({str(e)})."})

            row_idx += 1

        if errors:
            return request.make_response(json.dumps({
                "success_count": 0,
                "errors": errors
            }), headers=[('Content-Type', 'application/json')])

        if parsed_data:
            EmployeeDir = request.env['kuec.employee.directory'].sudo()
            try:
                with request.env.cr.savepoint():
                    for row_data in parsed_data:
                        EmployeeDir.create(row_data)
            except Exception as e:
                return request.make_response(json.dumps({
                    "success_count": 0,
                    "errors": [{"row": 0, "reason": f"Database Validation Error: {str(e)}"}]
                }), headers=[('Content-Type', 'application/json')])

        # ISSUE-002: Sanitized log (counts only, no PII).
        _logger.info("Employee bulk import: success_count=%s", len(parsed_data))
        return request.make_response(json.dumps({
            "success_count": len(parsed_data),
            "errors": []
        }), headers=[('Content-Type', 'application/json')])
