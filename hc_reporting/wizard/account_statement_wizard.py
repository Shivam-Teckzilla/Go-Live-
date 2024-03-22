from odoo import models, fields, api
from io import BytesIO
import io
import base64
from datetime import datetime
import xlrd.xldate
from odoo.tools.misc import xlwt


class AccountReportWizard(models.TransientModel):
    _name = 'account.report.wizard'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    partner_type = fields.Selection([
        ('creditor', 'Creditor'),
        ('debtor', 'Debtor')],
        string='Report Type')
    invoice_data = fields.Many2many('account.move', string='Invoice Data')

    def report_xls_print(self):
        if self.partner_type == 'creditor':
            filename = 'Creditors.xls'
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
            style_title = xlwt.easyxf(
                'font:height 300,bold True; align: horiz center; borders: left thin, right thin, top thin, bottom thin;')

            style = xlwt.easyxf("font:height 200,bold True; font: name Liberation Sans,color black;")
            worksheet = workbook.add_sheet('Sheet 1')

            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'DD-MM-YYY'
            worksheet.col(0).width = 8000
            worksheet.row(0).height = 300
            worksheet.col(1).width = 8000
            worksheet.row(1).height = 300

            worksheet.write_merge(0, 1, 0, 0, 'Name of Creditors', style_title)
            worksheet.write_merge(0, 1, 1, 1, 'GST NO.', style_title)
            worksheet.write_merge(0, 0, 2, 4, 'Invoice Detail', style_title)
            worksheet.write_merge(0, 0, 5, 5, 'Against Letter of Credit', style)
            worksheet.write_merge(0, 0, 6, 6, 'Selected Related Party', style)
            worksheet.write_merge(1, 1, 5, 5, 'Select Y for Yes & N for No', style)
            worksheet.write_merge(1, 1, 6, 6, 'G for government & R for Associate O for Others', style)
            worksheet.write_merge(1, 1, 2, 2, 'No.', style_title)
            worksheet.write_merge(1, 1, 3, 3, 'Date.', style_title)
            worksheet.write_merge(1, 1, 4, 4, 'Value.', style_title)

            invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('invoice_date', '>=', self.start_date),
                ('invoice_date', '<=', self.end_date),
                ('state', '=', 'posted'),
            ])

            row_index = 2

            for invoice in invoices:
                if invoice.l10n_in_gst_treatment == 'overseas':
                    gst = '99EXPOR0000E9Z9'
                else:
                    gst = '88INDIG0000I8Z8'
                worksheet.write(row_index, 0, invoice.partner_id.name, style)
                worksheet.write(row_index, 1, invoice.partner_id.vat or gst, style)
                worksheet.write(row_index, 2, invoice.name, style)
                worksheet.write(row_index, 3, invoice.invoice_date, date_format)
                worksheet.write(row_index, 4, invoice.amount_total, style)
                row_index += 1

            fp = io.BytesIO()
            workbook.save(fp)
            export_id = self.env['account.report.excel'].create(
                {'excel_file': base64.b64encode(fp.getvalue()), 'file_name': filename})

            res = {
                'view_mode': 'form',
                'res_id': export_id.id,
                'res_model': 'account.report.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
            return res

        if self.partner_type == 'debtor':
            filename = 'Debtors.xls'
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
            style_title = xlwt.easyxf(
                'font:height 300,bold True; align: horiz center; borders: left thin, right thin, top thin, bottom thin;')

            style = xlwt.easyxf("font:height 200,bold True; font: name Liberation Sans,color black;")
            worksheet = workbook.add_sheet('Sheet 1')

            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'YYYY-MM-DD'

            worksheet.col(0).width = 8000
            worksheet.row(0).height = 300
            worksheet.col(1).width = 8000
            worksheet.row(1).height = 300
            worksheet.col(5).width = 8000
            worksheet.row(5).height = 300
            worksheet.col(6).width = 8000
            worksheet.row(6).height = 300

            worksheet.write_merge(0, 1, 0, 0, 'Name of Debtors', style_title)
            worksheet.write_merge(0, 1, 1, 1, 'GST NO.', style_title)
            worksheet.write_merge(0, 0, 2, 4, 'Invoice Detail', style_title)
            worksheet.write_merge(0, 0, 5, 5, 'Discounted', style)
            worksheet.write_merge(0, 0, 6, 6, 'Selected Related Party', style)
            worksheet.write_merge(1, 1, 2, 2, 'No.', style_title)
            worksheet.write_merge(1, 1, 3, 3, 'Date', style_title)
            worksheet.write_merge(1, 1, 4, 4, 'Value', style_title)
            worksheet.write_merge(1, 1, 5, 5, 'Select Y for Yes & N for No', style)
            worksheet.write_merge(1, 1, 6, 6, 'G for government & R for Associate O for Others', style)

            invoices = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('invoice_date', '>=', self.start_date),
                ('invoice_date', '<=', self.end_date),
                ('state', '=', 'posted'),
            ])

            row_index = 2

            for invoice in invoices:
                if invoice.l10n_in_gst_treatment == 'overseas':
                    gst = '99EXPOR0000E9Z9'
                else:
                    gst = '88INDIG0000I8Z8'
                worksheet.write(row_index, 0, invoice.partner_id.name, style)
                worksheet.write(row_index, 1, invoice.partner_id.vat or gst, style)
                worksheet.write(row_index, 2, invoice.name, style)
                worksheet.write(row_index, 3, invoice.invoice_date, date_format)
                worksheet.write(row_index, 4, invoice.amount_total, style)
                row_index += 1

            fp = io.BytesIO()
            workbook.save(fp)
            export_id = self.env['account.report.excel'].create(
                {'excel_file': base64.b64encode(fp.getvalue()), 'file_name': filename})

            res = {
                'view_mode': 'form',
                'res_id': export_id.id,
                'res_model': 'account.report.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
            return res


class Account_report_excel(models.TransientModel):
    _name = "account.report.excel"
    _description = "Account Report Excel"

    excel_file = fields.Binary('Account Report')
    file_name = fields.Char('Excel File', size=64)
