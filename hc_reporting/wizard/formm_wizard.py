from odoo import fields, models, api, _
from datetime import date, timedelta, datetime
from odoo.tools.misc import xlwt
from io import  BytesIO
import io
import base64
from datetime import datetime
import xlrd.xldate


class SaleReportingWizard(models.TransientModel):
    _name = 'sale.reporting.wizard'

    
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    consigner_id=fields.Many2many('res.partner', string="Consigner Name")
    commodity_id=fields.Many2many('product.template', string="Commodity")
    file_name = fields.Binary('Excel Report')
    data = fields.Char('Excel File', size=64)
    filename = fields.Char('Excel File', size=64)
    report_select = fields.Selection([
        ('stock', 'Stock'),
        ('purchase', 'Purchase'),
    ], string="Select Report Type", required=True)


    def form_report_print(self):
        filename = 'M Return Grain Trail.xls'
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
        style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz left")
        style = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black;")
        worksheet = workbook.add_sheet('Sheet 1')
        margin_style = xlwt.easyxf("font: name Liberation Sans,color red;")
        title = "FORM M"
       
        move_records = self.env['sale.order'].search([
                ('date_order', '>=', self.start_date),
                ('date_order', '<=', self.end_date),
                # ('order_line.product_id.id', 'in', self.commodity_id.ids),
            ])
        worksheet.write_merge(1,1, 1, 10, title, style=style_title)
        worksheet.write_merge(2,2, 1, 10, "Return of Daily Purchase and Sales", style=style_title)
        worksheet.write_merge(3,3, 1, 10, 'MARKET COMMITTEE : -   BANUR', style=style_title)


        worksheet.write(5, 1,'DATE :-',style_table_header)

        worksheet.write(5, 5, 'COUNTERFOIL', style=style_title)
        worksheet.write(5, 9,'LICENCE NO :- ', style_table_header,)
        worksheet.write(6, 1, 'NAME OF THE DEALER :- ', style_table_header)
        worksheet.write(6, 9,'PERIOD :- ', style_table_header,)
        worksheet.write(6, 10, str(self.start_date) + ' TO ' + str(self.end_date), style_table_header)
        
        worksheet.write_merge(11,11, 1,5, 'LAST DATE WHEN MARKET FEE PAID WITH RECEIPT NO :- NOT APPLICABLE', style_table_header,)
        # worksheet.write(40, 9,'SIGNATURE OF THE DEALER', style_table_header,)


        worksheet.write(15, 1, 'DATE OF TRANSACTION', style_title)
        worksheet.write(15, 2, 'NAME OF COMMODITY', style_title)
        worksheet.write(15, 3, 'NAME OF SELLER FROM WHOM PURCHASED ', style_title)
        worksheet.write(15, 4, 'ADDRESS', style_title)
        worksheet.write(15, 6, 'WEIGHT', style_title)
        worksheet.write(15, 7, 'RATE', style_title)
        worksheet.write(15, 8, 'VALUE', style_title)
        worksheet.write(15, 9, 'WHETHER FEE IS LEVIABLE OR NOT,WHY ?', style_title)

        worksheet.write(15, 10, 'AMOUNT OF FEE LEVIABLE *[(A) FROM BUYER (B) FROM PRODUCER ( C ) TOTAL]', style_title)
        row = 16  

        for order in move_records:
            for line in order.order_line:
                worksheet.write(row, 1, order.date_order.strftime('%Y-%m-%d')) 
                worksheet.write(row, 2, line.product_id.name)  
                worksheet.write(row, 3, order.company_id.name)
                worksheet.write(row, 4, order.company_id.street) 
                worksheet.write(row, 6, line.product_uom_qty) 
                worksheet.write(row, 7, line.price_unit) 
                worksheet.write(row, 8, line.price_subtotal)  
                row += 1


        if self.report_select == 'stock':

            worksheet.write(7, 3, 'WORKS :- ', style_table_header)
            worksheet.write(7, 8,'CONSIGNER :-', style_table_header,)
            worksheet.write(8, 3, 'GSTIN :- ', style_table_header)
            worksheet.write(9, 3, 'GODOWN :- ', style_table_header)
            worksheet.write(13, 5, 'STOCK TRANSFER', style=style_title)
            worksheet.write(10, 8,'CONSIGNEE :-', style_table_header,)
            worksheet.write(15, 5, 'CHALLAN NO.', style_title)
           


        if self.report_select == 'purchase':

            worksheet.write(13, 5, 'PURCHASE STATEMENT', style=style_title)
            worksheet.write(15, 5, 'R.O NO.', style_title)

           

        fp = io.BytesIO()
        workbook.save(fp)
        export_id = self.env['sale.report.excel'].create({'excel_file': base64.b64encode(fp.getvalue()), 'file_name': filename})
        res = {
                'view_mode': 'form',
                'res_id': export_id.id,
                'res_model': 'sale.report.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target':'new'
                }
        return res

    
    

class sale_report_excel(models.TransientModel):
    _name = "sale.report.excel"
    _description="Sale Report Excel"

    excel_file = fields.Binary('Report')
    file_name = fields.Char('Excel File', size=64)

