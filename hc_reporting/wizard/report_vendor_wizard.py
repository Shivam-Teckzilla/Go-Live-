from odoo import models, fields, api
from io import  BytesIO
import io
import base64
from datetime import datetime
import xlrd.xldate
from odoo.tools.misc import xlwt


class CustomerReportWizard(models.TransientModel):
	_name = 'customer.report.wizard'

	start_date = fields.Date(string='Start Date')
	end_date = fields.Date(string='End Date')
	partner_type = fields.Selection([
		('vendor', 'Vendor'),
		('salary', 'Salary')],
		string='Report Type')
	invoice_data = fields.Many2many('account.move', string='Invoice Data')


	def report_xls_print(self):
		if self.partner_type == 'vendor':
			filename = 'Pending Payments.xls'
			workbook = xlwt.Workbook()
			stylePC = xlwt.XFStyle()
			alignment = xlwt.Alignment()
			alignment.horz = xlwt.Alignment.HORZ_CENTER
			fontP = xlwt.Font()
			fontP.bold = True
			fontP.height = 200
			stylePC.font = fontP
			stylePC.num_format_str = '@'
			stylePC.alignment = alignment
			style_title = xlwt.easyxf("font:height 200;pattern: pattern solid, pattern_fore_colour gray25; font: name Liberation Sans, bold on,color black; align: horiz center")
			style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center")
			style = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black;")
			worksheet = workbook.add_sheet('Sheet 1')
			margin_style = xlwt.easyxf("font: name Liberation Sans,color red;")
			date_format = xlwt.XFStyle()
			date_format.num_format_str = 'YYYY-MM-DD' 




			row_index = 0

			invoices = self.env['account.move'].search([
			('move_type', '=', 'in_invoice'), 
			('invoice_date', '>=', self.start_date),
			('invoice_date', '<=', self.end_date),
			('state', '=', 'posted'),
				])


			for invoice in invoices:
				worksheet.write(row_index, 0, invoice.name, style)
				worksheet.write(row_index, 1, invoice.company_id.name, style)
				pending_amount = invoice.amount_total
				payment_type = ""
			
				if pending_amount < 100000:
					payment_type = "IMPS"
				elif 100000 <= pending_amount <= 200000:
					payment_type = "NEFT"
				else:
					payment_type = "RTGS"
			
				worksheet.write(row_index, 2, f"{payment_type}", style)
			
				worksheet.write(row_index, 3, invoice.invoice_date, date_format)
				worksheet.write(row_index, 4, invoice.amount_total, style)
				worksheet.write(row_index, 5, invoice.partner_id.name, style)  
				worksheet.write(row_index, 6, invoice.partner_id.bank_ids.acc_number, style) 
				worksheet.write(row_index, 7, invoice.partner_id.bank_ids.bank_id.name, style)  
				worksheet.write(row_index, 8, invoice.partner_id.email, style)
				worksheet.write(row_index, 9, invoice.partner_id.mobile if invoice.partner_id.mobile else None, style)

				row_index += 1


			fp = io.BytesIO()
			workbook.save(fp)
			export_id = self.env['vendor.report.excel'].create({'excel_file': base64.b64encode(fp.getvalue()), 'file_name': filename})

			res = {
					'view_mode': 'form',
					'res_id': export_id.id,
					'res_model': 'vendor.report.excel',
					'view_type': 'form',
					'type': 'ir.actions.act_window',
					'target':'new'
					}
			return res
		
		if self.partner_type == 'salary':
			filename = 'Pending Payments.xls'
			workbook = xlwt.Workbook()
			stylePC = xlwt.XFStyle()
			alignment = xlwt.Alignment()
			alignment.horz = xlwt.Alignment.HORZ_CENTER
			fontP = xlwt.Font()
			fontP.bold = True
			fontP.height = 200
			stylePC.font = fontP
			stylePC.num_format_str = '@'
			stylePC.alignment = alignment
			style_title = xlwt.easyxf("font:height 200;pattern: pattern solid, pattern_fore_colour gray25; font: name Liberation Sans, bold on,color black; align: horiz center")
			style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center")
			style = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black;")
			worksheet = workbook.add_sheet('Sheet 1')
			margin_style = xlwt.easyxf("font: name Liberation Sans,color red;")
			date_format = xlwt.XFStyle()
			date_format.num_format_str = 'YYYY-MM-DD' 
			
			row_index = 0
	
			contracts = self.env['hr.contract'].search([
				('date_start', '<=', self.end_date),
				('date_end', '>=', self.start_date),
				('state', '=', 'open'),
			])
		
			for contract in contracts:
				employee = contract.employee_id
				worksheet.write(row_index, 0, contract.name, style)
				worksheet.write(row_index, 1, employee.company_id.name, style)
				pending_amount = contract.wage
				payment_type = ""
			
				if pending_amount < 100000:
					payment_type = "IMPS"
				elif 100000 <= pending_amount <= 200000:
					payment_type = "NEFT"
				else:
					payment_type = "RTGS"
			
				worksheet.write(row_index, 2, f"{payment_type}", style)
			
				worksheet.write(row_index, 3, contract.date_start, date_format)
				worksheet.write(row_index, 4, contract.wage, style) 
				worksheet.write(row_index, 5, employee.work_contact_id.name, style)
				worksheet.write(row_index, 6, employee.work_contact_id.bank_ids.bank_id.name, style) 
				worksheet.write(row_index, 7, employee.work_contact_id.bank_ids.acc_number, style)  
				worksheet.write(row_index, 8, employee.work_contact_id.email, style)
				worksheet.write(row_index, 9, employee.work_contact_id.mobile if employee.work_contact_id.mobile else None, style)

				row_index += 1
					
	
			
	
	
			fp = io.BytesIO()
			workbook.save(fp)
			export_id = self.env['vendor.report.excel'].create({'excel_file': base64.b64encode(fp.getvalue()), 'file_name': filename})
	
			res = {
					'view_mode': 'form',
					'res_id': export_id.id,
					'res_model': 'vendor.report.excel',
					'view_type': 'form',
					'type': 'ir.actions.act_window',
					'target':'new'
					}
			return res




class vendor_report_excel(models.TransientModel):
	_name = "vendor.report.excel"
	_description="vendor Report Excel"

	excel_file = fields.Binary('Vendor Report')
	file_name = fields.Char('Excel File', size=64)