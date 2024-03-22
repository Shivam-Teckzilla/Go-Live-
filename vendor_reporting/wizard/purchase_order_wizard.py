from odoo import fields, models, api, _
from datetime import date, timedelta, datetime
from odoo.tools.misc import xlwt
from io import  BytesIO
import io
import base64
from datetime import datetime
import xlrd.xldate


class PurchaseReportingWizard(models.TransientModel):
    _name = 'purchase.reporting.wizard'

    
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    vendor_id=fields.Many2many('res.partner', string="Select Vendor")
    product_name=fields.Many2many('product.product', string="Select Product")
    selected = fields.Boolean("Only Select Vendor")
    selected_pro = fields.Boolean("Only Select Product")
    file_name = fields.Binary('Excel Report')
    data = fields.Char('Excel File', size=64)
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
            return self.env.ref('vendor_reporting.purchase_vendor_report_pdf').report_action(self, data=data)
        
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
        style_title = xlwt.easyxf("font:height 200;pattern: pattern solid, pattern_fore_colour gray25; font: name Liberation Sans, bold on,color black; align: horiz center")
        style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center")
        style = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black;")
        worksheet = workbook.add_sheet('Sheet 1')
        margin_style = xlwt.easyxf("font: name Liberation Sans,color red;")
        title = "All Vendor Purchase Order Report"

        move_records = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date),
            ])

        
        worksheet.write_merge(1,1, 1, 18, title, style=style_title)

        worksheet.write(3, 3,'Date From:',style_table_header)
        worksheet.write(3, 4, str(self.start_date), style_table_header)
        worksheet.write(3, 8,'Date To:', style_table_header,)
        worksheet.write(3, 9, str(self.end_date), style_table_header)
        worksheet.write(3, 12,'Licence No:', style_table_header,)
        worksheet.write(4, 1, 'Name OF The Dealer :', style_title)
        worksheet.write(4, 12, 'Consigner :', style_title)
        worksheet.write(5, 2, 'Works :', style)
        worksheet.write(6, 2, 'GSTIN :', style)
        worksheet.write(7, 2, 'GODOWN :', style)
        worksheet.write(8, 1, 'Last Date When Market Fee Paid With Receipt No :', style_title)
      
    


        worksheet.write(11, 1, 'Vendor Code', style_title)
        worksheet.write(11, 2, 'Vendor Name', style_title)
        worksheet.write(11, 3, 'PO Number', style_title)
        worksheet.write(11, 4, 'PO Date', style_title)
        worksheet.write(11, 5, 'Item Name', style_title)
        worksheet.write(11, 6, 'UOM', style_title)
        worksheet.write(11, 7, 'Demanded QTY', style_title)
        worksheet.write(11, 8, 'Received QTY', style_title)
        worksheet.write(11, 9, 'Pending QTY', style_title)
        worksheet.write(11, 10, 'Expected Delivery Date', style_title)
        worksheet.write(11, 11, 'GRN Number', style_title)
        worksheet.write(11, 12, 'GRN Date', style_title)
        worksheet.write(11, 13, 'PO Over Date', style_title)
        worksheet.write(11, 14, 'Pysically Verified By', style_title)
        worksheet.write(11, 15, 'QC Date', style_title)
        worksheet.write(11, 16, 'Strach', style_title)
        worksheet.write(11, 17, 'FM', style_title)
        worksheet.write(11, 18, 'Moisture', style_title)


        row_index = 12
        clos = 0

        for move in move_records:
            for invoice_line in move.invoice_line_ids:
                worksheet.write(row_index, 1, move.partner_id.name, style)
                worksheet.write(row_index, 3, invoice_line.purchase_order_id.name, style)
                worksheet.write(row_index, 4, str(invoice_line.purchase_order_id.date_order), style)
                worksheet.write(row_index, 5, invoice_line.purchase_order_id.order_line.product_id.name, style)
                worksheet.write(row_index, 7, invoice_line.purchase_order_id.order_line.product_qty, style)
                worksheet.write(row_index, 8, invoice_line.purchase_order_id.order_line.qty_received, style)
                worksheet.write(row_index, 9, (invoice_line.purchase_order_id.order_line.product_qty)-(invoice_line.purchase_order_id.order_line.qty_received), style)
                worksheet.write(row_index, 10, str(invoice_line.purchase_order_id.order_line.date_planned), style)
                row_index += 1
                    

        fp = io.BytesIO()
        workbook.save(fp)
        export_id = self.env['purchase.report.excel'].create({'excel_file': base64.b64encode(fp.getvalue()), 'file_name': filename})

        res = {
                'view_mode': 'form',
                'res_id': export_id.id,
                'res_model': 'purchase.report.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target':'new'
                }
        return res




class purchase_report_excel(models.TransientModel):
    _name = "purchase.report.excel"
    _description="Purchase Report Excel"

    excel_file = fields.Binary('all Vendor Purchase Excel Report')
    file_name = fields.Char('Excel File', size=64)
