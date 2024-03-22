from odoo import fields, models, api, _
from datetime import date, timedelta, datetime
from odoo.tools.misc import xlwt
from io import BytesIO
import io
import base64
import xlrd.xldate
import xlsxwriter


class PurchaseReportingWizard(models.TransientModel):
    _name = 'purchase.reporting.wizard'

    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    vendor_id = fields.Many2many('res.partner', string="Select Vendor")
    product_name = fields.Many2many('product.product', string="Select Product")
    selected = fields.Boolean("Only Select Vendor")
    selected_pro = fields.Boolean("Only Select Product")
    file_name = fields.Binary('Excel Report')
    data = fields.Char('Data', size=64)
    filename = fields.Char('Excel File', size=64)
    report_select = fields.Selection([
        ('pdf', 'PDF Report'),
        ('xls', 'XLS Report'),
    ], string="Select Report Type", required=True)

    def report_print(self):
        if self.report_select == 'pdf':

            if self.selected_pro:
                product_ids = self.product_name.ids

            else:
                product_ids = self.env['product.product'].search([]).ids

            data = {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'vendor_ids': self.vendor_id.ids,
                'product_name': product_ids,
                'selected': self.selected,
                'selected_pro': self.selected_pro,
            }
            return self.env.ref('hc_reporting.purchase_vendor_report_pdf').report_action(self, data=data)

        if self.report_select == 'xls':
            return self.report_xls_print()

    def report_xls_print(self):
        filename = 'All Vendor Purchase Report.xls'
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
            "font:height 200;pattern: pattern solid, pattern_fore_colour gray25; font: name Liberation Sans, bold on,color black; align: horiz center")
        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center")
        style = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black;")
        worksheet = workbook.add_sheet('Sheet 1')
        margin_style = xlwt.easyxf("font: name Liberation Sans,color red;")
        title = "All Vendor Purchase Order Report"

        move_records = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ])

        worksheet.write_merge(1, 1, 1, 18, title, style=style_title)

        worksheet.write(3, 3, 'Date From:', style_table_header)
        worksheet.write(3, 4, str(self.start_date), style_table_header)
        worksheet.write(3, 8, 'Date To:', style_table_header, )
        worksheet.write(3, 9, str(self.end_date), style_table_header)

        worksheet.write(6, 1, 'Vendor Code', style_title)
        worksheet.write(6, 2, 'Vendor Name', style_title)
        worksheet.write(6, 3, 'PO Number', style_title)
        worksheet.write(6, 4, 'PO Date', style_title)
        worksheet.write(6, 5, 'Item Name', style_title)
        worksheet.write(6, 6, 'UOM', style_title)
        worksheet.write(6, 7, 'Demanded QTY', style_title)
        worksheet.write(6, 8, 'Received QTY', style_title)
        worksheet.write(6, 9, 'Pending QTY', style_title)
        worksheet.write(6, 10, 'Expected Delivery Date', style_title)
        worksheet.write(6, 11, 'GRN Number', style_title)
        worksheet.write(6, 12, 'GRN Date', style_title)
        worksheet.write(6, 13, 'PO Over Date', style_title)
        worksheet.write(6, 14, 'Pysically Verified By', style_title)
        worksheet.write(6, 15, 'QC Date', style_title)
        worksheet.write(6, 16, 'Strach', style_title)
        worksheet.write(6, 17, 'FM', style_title)
        worksheet.write(6, 18, 'Moisture', style_title)

        row_index = 7
        clos = 0

        for move in move_records:
            for invoice_line in move.invoice_line_ids:
                worksheet.write(row_index, 1, move.partner_id.name, style)
                worksheet.write(row_index, 3, invoice_line.purchase_order_id.name, style)
                worksheet.write(row_index, 4, str(invoice_line.purchase_order_id.date_order), style)
                worksheet.write(row_index, 5, invoice_line.purchase_order_id.order_line.product_id.name, style)
                worksheet.write(row_index, 7, invoice_line.purchase_order_id.order_line.product_qty, style)
                worksheet.write(row_index, 8, invoice_line.purchase_order_id.order_line.qty_received, style)
                worksheet.write(row_index, 9, (invoice_line.purchase_order_id.order_line.product_qty) - (
                    invoice_line.purchase_order_id.order_line.qty_received), style)
                worksheet.write(row_index, 10, str(invoice_line.purchase_order_id.order_line.date_planned), style)
                row_index += 1

        fp = io.BytesIO()
        workbook.save(fp)
        export_id = self.env['purchase.report.excel'].create(
            {'excel_file': base64.b64encode(fp.getvalue()), 'file_name': filename})

        res = {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'purchase.report.excel',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
        return res


class purchase_report_excel(models.TransientModel):
    _name = "purchase.report.excel"
    _description = "Purchase Report Excel"

    excel_file = fields.Binary('Report Download')
    file_name = fields.Char('Excel File', size=64)


# For Excel Report (Pending and booked)

class PurchaseOrderReportWizard(models.TransientModel):
    _name = 'purchase.order.report.wizard'
    _description = 'Purchase Order Report Wizard'

    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    vendor_id = fields.Many2many('res.partner', string="Select Vendor")
    product_name = fields.Many2many('product.product', string="Select Product")
    file_name = fields.Binary('Excel Report')
    data = fields.Char('Data', size=64)
    filename = fields.Char('Filename', size=64)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
    product_categ_id = fields.Many2one('product.category', string="Product Category")
    order_type = fields.Selection([
        ('pending', 'Pending Orders'),
        ('booked', 'Booked Orders')
    ], string='Order Type', required=True, default='pending')

    def print_excel_report(self):
        if self.order_type == 'pending':
            return self.print_pending_report()
        elif self.order_type == 'booked':
            return self.print_booked_report()

    # Pending Report
    def print_pending_report(self):
        filename = 'Pending.xlsx'
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()

        # Define styles
        title_format = workbook.add_format({
            'bold': True,
            'font_name': 'Arial',
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'bg_color': 'gray25',
            'font_color': 'white'
        })
        header_format = workbook.add_format({
            'bold': True,
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'bg_color': 'gray',
            'font_color': 'black'
        })
        data_format = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        date_format = workbook.add_format({
            'num_format': 'dd/mm/YYYY',
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        text_format = workbook.add_format({'font_size': 11, 'align': 'left', 'bold': True})


        # Write title and headers
        title = "Pending order (partial delivery)"
        worksheet.merge_range('A1:H1', title, title_format)
        worksheet.write('A3', 'Date From:', header_format)
        worksheet.write('B3', str(self.start_date), header_format)
        worksheet.write('D3', 'Date To:', header_format)
        worksheet.write('E3', str(self.end_date), header_format)
        worksheet.write('A4', 'HEAD :' +''+ str(self.product_categ_id.name),text_format) if self.product_categ_id else ''
        worksheet.write('A5', 'ITEM' +''+ str(self.product_name.mapped('name')),text_format) if self.product_name else ''
        worksheet.write_row('A6', ['P.O DATE', 'P.O NO', 'SUPPLIER', 'Order Days', 'P.O QTY', 'RATE', 'IN PLANT', 'BALANCE'],
                            header_format)

        # Write data
        row_index = 7
        current_date = datetime.today().date()

        domain = [('date_order', '>=', self.start_date),
                  ('date_order', '<=', self.end_date)]

        product_categ_filter_domain = ('categ_id', '=', self.product_categ_id.id)
        if self.product_categ_id:
            domain.append(product_categ_filter_domain)

        product_filter_domain = ('product_id', 'in', self.product_name.ids)
        if self.product_name:
            domain.append(product_filter_domain)

        vendor_domain = ('partner_id', 'in', self.vendor_id.ids)
        if self.vendor_id:
            domain.append(vendor_domain)

        company_domain = ('company_id', '=', self.company_id.id)
        if self.company_id:
            domain.append(company_domain)

        line_records = self.env['purchase.order.line'].search(domain)

        line_records_sorted = sorted(line_records, key=lambda l: l.order_id.name)

        for line in line_records:
            order_planned_date = line.order_id.date_approve.date()
            days_difference = (current_date - order_planned_date).days
            if line.qty_received:
                worksheet.write(row_index, 0, line.order_id.date_approve, date_format)
                worksheet.write(row_index, 1, line.order_id.name, data_format)
                worksheet.write(row_index, 2, line.order_id.partner_id.name, data_format)
                worksheet.write(row_index, 3, str(days_difference) , data_format)
                worksheet.write(row_index, 4, line.product_qty, data_format)
                worksheet.write(row_index, 5, line.price_unit, data_format)
                row_index += 1

        workbook.close()

        # Return the file
        with open(filename, 'rb') as f:
            file_data = f.read()
        export_id = self.env['purchase.report.excel'].create({
            'excel_file': base64.b64encode(file_data),
            'file_name': filename
        })

        res = {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'purchase.report.excel',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
        return res

    # Booked Report

    def print_booked_report(self):
        filename = 'Booked.xlsx'
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()

        # Define styles
        title_format = workbook.add_format({
            'bold': True,
            'font_name': 'Arial',
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'bg_color': 'gray25',
            'font_color': 'white'
        })
        header_format = workbook.add_format({
            'bold': True,
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'bg_color': 'gray',
            'font_color': 'black'
        })
        data_format = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        date_format = workbook.add_format({
            'num_format': 'dd/mm/YYYY',
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        text_format = workbook.add_format({'font_size': 11, 'align': 'left', 'bold': True})


        # Write title and headers
        worksheet.merge_range('A1:F1', 'Booked order (order booked but not received)', title_format)
        worksheet.write('A3', 'Date From:', header_format)
        worksheet.write('B3', str(self.start_date), header_format)
        worksheet.write('D3', 'Date To:', header_format)
        worksheet.write('E3', str(self.end_date), header_format)
        worksheet.write('A4', 'HEAD :' + '' + str(self.product_categ_id.name),
                        text_format) if self.product_categ_id else ''
        worksheet.write('A5', 'ITEM' + '' + str(self.product_name.mapped('name')),
                        text_format) if self.product_name else ''
        worksheet.write_row('A6', ['P.O DATE', 'P.O NO', 'SUPPLIER', 'P.O QTY', 'RATE', 'VALID'], header_format)

        # Write data
        row_index = 7
        current_date = datetime.today().date()

        domain = [('date_order', '>=', self.start_date),
                  ('date_order', '<=', self.end_date)]

        product_filter_domain = ('product_id', 'in', self.product_name.ids)
        if self.product_name:
            domain.append(product_filter_domain)

        vendor_domain = ('partner_id', 'in', self.vendor_id.ids)
        if self.vendor_id:
            domain.append(vendor_domain)

        company_domain = ('company_id', '=', self.company_id.id)
        if self.company_id:
            domain.append(company_domain)

        line_records = self.env['purchase.order.line'].search(domain)

        line_records_sorted = sorted(line_records, key=lambda l: l.order_id.name)

        for line in line_records:
            order_planned_date = line.order_id.date_approve.date()
            days_difference = (current_date - order_planned_date).days
            if not line.qty_received:
                worksheet.write(row_index, 0, line.order_id.date_approve, date_format)
                worksheet.write(row_index, 1, line.order_id.name, data_format)
                worksheet.write(row_index, 2, line.order_id.partner_id.name, data_format)
                worksheet.write(row_index, 3, line.product_qty, data_format)
                worksheet.write(row_index, 4, line.price_unit, data_format)
                worksheet.write(row_index, 5, days_difference, data_format)
                worksheet.write(row_index, 6, line.order_id.date_planned, data_format)
                row_index += 1

        workbook.close()

        # Return the file
        with open(filename, 'rb') as f:
            file_data = f.read()
        export_id = self.env['purchase.report.excel'].create({
            'excel_file': base64.b64encode(file_data),
            'file_name': filename
        })

        res = {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'purchase.report.excel',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
        return res