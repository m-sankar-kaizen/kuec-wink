from odoo import models, fields, api, _
import xlwt
from io import BytesIO
import base64
from odoo.osv import expression
import openpyxl
from openpyxl import Workbook

from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
import base64


class HrPayslipRun(models.Model):
    """
        Inherits the hr.payslip.run model to add functionality for generating
        Excel reports related to employee educational fees and annual ticket processing.

        Methods:
            - print_educational_fees():
                Generates an Excel report listing the educational fee history for children
                related to employees in the payslip run.

            - print_annual_ticket():
                Generates an Excel report summarizing annual ticket information, employee assignment details,
                and payment data for employees included in the payslip run.
        """
    _inherit = 'hr.payslip.run'

    def print_educational_fees(self):
        """
                Generate an Excel report titled 'Education Fees History' for the current payslip run,
                listing detailed information about educational fee payments related to children
                linked to employee contracts.

                Returns:
                    dict: An Odoo action dictionary to download the generated Excel report as an attachment.
                """
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'Education Fees History '

        # Headers based on the screenshot
        headers = [
            "Emp #", "Name", "Birthday", "Reference #", "Academic Year", "Semester", "Child",
            "Grade", "Total Paid Before", "Book", "Transportation", "Tuition", "Amount Requested",
            "Child Entitlement", "Amount Paid", "Pay to", "Created On", "School"
        ]

        # Set column widths (approximated)
        column_widths = [20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20]
        for i, width in enumerate(column_widths, start=1):
            worksheet.column_dimensions[get_column_letter(i)].width = width

        # Define styles
        header_fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
        header_font = Font(bold=True)
        header_alignment = Alignment(horizontal="center", vertical="center")

        # Create headers
        for col_num, header in enumerate(headers, start=1):
            cell = worksheet.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        row, col = 2, 1

        for slip in self.slip_ids:
            if slip.contract_id:
                for line in slip.contract_id.child_contract_line_ids:
                    worksheet.cell(row=row, column=col,
                                   value=slip.employee_id.ku_number if slip.employee_id.ku_number else "")
                    col += 1
                    worksheet.cell(row=row, column=col, value=slip.employee_id.name)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.birth_day)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.reference)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.academic)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.semester)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.child_name)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.grade)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.total_paid_before)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.book)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.transportation)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.tuition)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.amount_requested)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.child_entitlement)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.amount_paid)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.paid_to)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.created_on)
                    col += 1
                    worksheet.cell(row=row, column=col, value=line.school)
                    col += 1
                    col = 1
                    row += 1

        # Second worksheet


        # Save the workbook to a BytesIO object
        report_file = BytesIO()
        workbook.save(report_file)
        report_file.seek(0)

        # Create an attachment in Odoo
        filename = 'Ankabut_Education_supplementary_batch' + self.date_end.strftime("%B %Y") + ".xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.encodebytes(report_file.read()),
            'res_model': self._name,
            'res_id': self.id
        })

        # Return the URL for downloading the file
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }

    def print_annual_ticket(self):
        """
                Generate an Excel report titled 'Annual Ticket Process' for the current payslip run,
                summarizing ticket-related details, assignment info, and payments for employees.

                Returns:
                    dict: An Odoo action dictionary to download the generated Excel report as an attachment.
                """
        workbook = Workbook()
        # Create a new sheet with data and set it as active
        annual_worksheet = workbook.active
        annual_worksheet.title = 'Annual Ticket Process'
        # Second worksheet
        for i in range(1, 38):
            annual_worksheet.column_dimensions[get_column_letter(i)].width = 20

        annual_worksheet.row_dimensions[2].height = 30
        annual_worksheet.row_dimensions[1].height = 30
        annual_worksheet.row_dimensions[3].height = 30
        annual_worksheet.title = 'Annual Ticket Process'
        title = "Annual Ticket Process - Ankabut - July 2024 Supplementary Batch1"
        annual_worksheet.merge_cells('C1:AL1')
        title_cell = annual_worksheet['C1']
        title_cell.value = title

        # Apply styles to the title cell
        title_cell.font = Font(size=14, bold=True)
        title_cell.alignment = Alignment(horizontal="center", vertical="center")

        # Define categories and their spans
        categories = {
            str(fields.Date().today().year - 1) + " - Fares": ('R2:T2'),
            str(fields.Date().today().year) + " - Fares": ('U2:W2'),
            "Dependent Details": ('X2:AB2'),
            "Outstanding Payments": ('AC2:AG2')
        }

        # Apply styles and merge cells for categories
        category_fill = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid")
        category_font = Font(bold=True)
        category_alignment = Alignment(horizontal="center", vertical="center")

        for category, span in categories.items():
            annual_worksheet.merge_cells(span)
            cell = annual_worksheet[span.split(':')[0]]
            cell.value = category
            cell.fill = category_fill
            cell.font = category_font
            cell.alignment = category_alignment

        # Fill cells between C2 and Q2 with blue fill color
        for col in range(3, 18):
            cell = annual_worksheet.cell(row=2, column=col)
            cell.fill = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")
        # Define header titles
        headers_row_2 = [
            "", "", "Annual Ticket Process - Ankabut - July 2024 Supplementary Batch1", "", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "2023 - Fares", "", "", "", "", "2024 - Fares", "", "", "", "", "Dependent Details",
            "", "", "", "", "", "", "Outstanding Payments", "", "", "", "", ""
        ]

        headers_row_3 = ["Emp #", "Employee Name", "Hire Date",
                         "Gender", "Marital Status", "Nationality", "Assignment Status", "Grade", "Organization",
                         "Payroll",
                         "Position", "Contract Type", "Assignment Category", "Payroll Period", "Ticket Zone",
                         "Country Code",
                         "Ticket Class", "Adult Ticket Amount", "Child Ticket Amount", "Infant Ticket Amount",
                         "Adult Ticket Amount",
                         "Child Ticket Amount", "Infant Ticket Amount", "Employee Count", "Spouse Count", "Adult Count",
                         "Child Count", "Infant Count", "Total Count", "Start Date", "End Date", "Days",
                         "Previous Outstanding",
                         "Year 2024 Payment", "Deductions/Adjustments", "Total Amount", "Remarks"
                         ]

        # Merge and set the title for the header row 2
        # annual_worksheet.merge_cells('C2:T2')
        # annual_worksheet['C2'] = headers_row_2[2]

        # Apply styles for the merged title cell
        title_cell = annual_worksheet['C2']
        title_cell.fill = PatternFill(start_color="FFCC99", end_color="FFCC99", fill_type="solid")
        title_cell.font = Font(size=14, bold=True)
        title_cell.alignment = Alignment(horizontal="center", vertical="center")

        # Apply styles and set values for header row 3
        header_fill = PatternFill(start_color="00CCFF", end_color="00CCFF", fill_type="solid")
        header_font = Font(bold=True)
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        header_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                               bottom=Side(style='thin'))

        for col_num, header in enumerate(headers_row_3, start=1):
            cell = annual_worksheet.cell(row=3, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = header_border

        row = 4
        col = 1
        for slip in self.slip_ids:
            previous_outstading = 0
            payment_year = 0

            if slip.contract_id:
                cont = slip.contract_id
                days = (cont.date_end - cont.date_start).days + 1 if cont.date_start and cont.date_end else 1
                payment_year += ((cont.adult_ticket_amount * (
                            cont.employee_count + cont.spouse_count + cont.adult_count)) + (
                                             cont.child_ticket_amount + cont.child_count) + (
                                             cont.infant_ticket_amount + cont.infant_count))
                previous_outstading += ((cont.adult_ticket_amount * (
                            cont.employee_count + cont.spouse_count + cont.adult_count)) + (
                                                    cont.child_ticket_amount + cont.child_count) + (
                                                    cont.infant_ticket_amount + cont.infant_count)) / (365 * days)
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.employee_id.ku_number if slip.employee_id.ku_number else "")
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.employee_id.name if slip.employee_id else "")
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.ku_hire_date if slip.contract_id else "")
                col += 1
                annual_worksheet.cell(row=row, column=col, value=slip.employee_id.gender if slip.employee_id else "")
                col += 1
                annual_worksheet.cell(row=row, column=col, value=slip.employee_id.marital if slip.employee_id else "")
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.employee_id.country_id.name if slip.employee_id and slip.employee_id.country_id else "")
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.assignment_status if slip.contract_id else "")
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.employee_id.grade_id.name if slip.employee_id and slip.employee_id.grade_id else "")
                col += 1

                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.organization if slip.contract_id else "")
                col += 1

                annual_worksheet.cell(row=row, column=col, value="ANKABUT Monthly Payroll")
                col += 1

                annual_worksheet.cell(row=row, column=col,
                                      value=slip.employee_id.job_id.name if slip.employee_id.job_id else "")
                col += 1

                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.contract_type_id.name if slip.contract_id.contract_type_id else "")
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.assignment_category)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=self.date_start)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.ticket_zone)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.employee_id.country_id.code if slip.employee_id.country_id else "")
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.ticket_class)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.prev_adult_ticket_amount)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.prev_child_ticket_amount)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.prev_infant_ticket_amount)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.adult_ticket_amount)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.child_ticket_amount)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.infant_ticket_amount)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.employee_count)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.spouse_count)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.adult_count)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.child_count)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.infant_count)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.total_count)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.date_start)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.date_end)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=(
                                                    slip.contract_id.date_end - slip.contract_id.date_start).days + 1 if slip.contract_id.date_start and slip.contract_id.date_end else 0)
                col += 1

                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.previous_outstanding)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.year_payment)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.deductions_adjustments)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value= slip.contract_id.total_amount)
                col += 1
                annual_worksheet.cell(row=row, column=col,
                                      value=slip.contract_id.remarks)
                col += 1
                row += 1
                col = 1

        # Save the workbook to a BytesIO object
        report_file = BytesIO()
        workbook.save(report_file)
        report_file.seek(0)

        # Create an attachment in Odoo
        filename = 'Ankabut_annual_ticket_batch' + self.date_end.strftime("%B %Y") + ".xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.encodebytes(report_file.read()),
            'res_model': self._name,
            'res_id': self.id
        })

        # Return the URL for downloading the file
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }
