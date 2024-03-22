import datetime
import json

from odoo import api, models, fields, _
import string
import xlsxwriter
import base64
from io import BytesIO


class SaudaReport(models.TransientModel):
    _name = "sauda.report"
    _rec_name = 'name'

    name = fields.Char(string='Name', default='Reports')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    partner_ids = fields.Many2many('res.partner', string='Vendor')
    purchase_ids = fields.Many2many('purchase.order', string='Purchase Order')

    file_name = fields.Char(string='File Name', readonly=True)
    output = fields.Binary(string='File', readonly=True)

    def xlsx_report(self):
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        worksheet = workbook.add_worksheet()

        # Alignment for excel sheet
        worksheet.set_column('A:K', 15)
        worksheet.set_column('L:BW', 17)
        worksheet.freeze_panes(2, 0)
        global year_format, month_format, date_format, output_format
        # Formatting For Data in Excel Sheet
        year_format = workbook.add_format(
            {'num_format': 'YYYY', 'font': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 8,
             'border': 1})
        month_format = workbook.add_format(
            {'num_format': 'mm', 'font': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 8, 'border': 1})
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/YYYY', 'font': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 8,
             'border': 1})
        title_format = workbook.add_format({
            'font_size': 8,
            'font': 'Arial',
            'border': 1,
            'text_wrap': True,
            'align': 'center',
            'bold': 1,
            'valign': 'vcenter'})
        output_format = workbook.add_format({
            'font_size': 8,
            'font': 'Arial',
            'align': 'left',
            'border': 1,
            'valign': 'vcenter'})
        header_format = workbook.add_format({
            'font_size': 11,
            'font': 'Arial',
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter'})

        # Heading for the values in Excel Sheet
        worksheet.merge_range('A1:B1', self.env.user.company_id.name, header_format)

        header = ['SR NO', 'LOADED', 'UNLOADED', 'BILL NO', 'TRUCK NO', 'RATE', 'DISPATCH', 'RECEIPT', 'STARCH',
                  'MOISTURE', 'FM', 'WT EXCESS', 'WEIGHT CUT', 'STARCH CUT', 'MOISTURE CUT', 'FM CUT', 'RATE DIFF']

        for index, value in enumerate(header):
            worksheet.write(1, index, value, title_format)
        from_date = (datetime.datetime.combine(self.from_date,datetime.datetime.strptime("00:00","%H:%M").time()))
        to_date = (datetime.datetime.combine(self.to_date,datetime.datetime.strptime("23:59","%H:%M").time()))

        search_domain = [('order_id.state', 'in', ['purchase', 'done'])]

        # Date Filter
        if self.from_date and self.to_date:
            search_domain.append(('order_id.date_approve', '>=', from_date))
            search_domain.append(('order_id.date_approve', '<=', to_date))

        if self.partner_ids:
            search_domain.append(('order_id.partner_id', 'in', self.partner_ids.ids))
        if self.purchase_ids:
            search_domain.append(('order_id', 'in', self.purchase_ids.ids))

        po_line = self.env['purchase.order.line'].search(search_domain)
        row = 2
        sr_no = 1
        for line in po_line:
            bills = line.order_id.invoice_ids.filtered(lambda x: x.state == 'posted')
            if bills:
                for bill in bills:
                    token_record = self.env['purchase.token'].search([('name_id', '=', line.order_id.id)])
                    for token in token_record:
                        pickings = self.env['stock.picking'].search(
                            [('origin', '=', line.order_id.name), ('token_id', '=', token.id), ('state', '=', 'done')])
                        if pickings:
                            for pick in pickings:
                                quality_check = self.env['quality.check'].search([('picking_id', '=', pick.id)])
                                if quality_check:
                                    for qc in quality_check:
                                        worksheet.write(row, 0, sr_no, output_format)
                                        worksheet.write(row, 1, token.weightment_in_datetime or ' ', date_format)
                                        worksheet.write(row, 2, token.weightment_out_datetime or ' ', date_format)
                                        worksheet.write(row, 3, bill.name, output_format)
                                        worksheet.write(row, 4, token.trailer, output_format)
                                        worksheet.write(row, 5, line.price_unit or 0.0, output_format)
                                        worksheet.write(row, 6, line.product_qty or ' ', output_format)
                                        worksheet.write(row, 7, line.qty_received or ' ', output_format)
                                        worksheet.write(row, 8, qc.starch or 0.0, output_format)
                                        worksheet.write(row, 9, qc.moisture or 0.0, output_format)
                                        worksheet.write(row, 10, qc.fm or 0.0, date_format)
                                        worksheet.write(row, 11, ' ', output_format)
                                        worksheet.write(row, 12, ' ', output_format)
                                        account_move_search = self.env['account.move'].search([('quality_check_id', '=', self.id), ('move_type', '=', 'in_refund')])

                                        if account_move_search.filtered(lambda x: 'Starch' in x.ref):
                                            worksheet.write(row, 13, account_move_search.filtered(lambda x: 'Starch' in x.ref).amount or ' ', output_format)
                                        else:
                                            worksheet.write(row, 13, ' ', output_format)

                                        if account_move_search.filtered(lambda x: 'Moisture' in x.ref):
                                            worksheet.write(row, 14, account_move_search.filtered(lambda x: 'Moisture' in x.ref).amount or ' ', output_format)
                                        else:
                                            worksheet.write(row, 14, ' ', output_format)

                                        if account_move_search.filtered(lambda x: 'Foreign matter' in x.ref):
                                            worksheet.write(row, 15, account_move_search.filtered(lambda x: 'Foreign matter' in x.ref).amount or ' ', output_format)
                                        else:
                                            worksheet.write(row, 15, ' ', output_format)

                                        worksheet.write(row, 16, ' ', output_format)
                                else:
                                    worksheet.write(row, 0, sr_no, output_format)
                                    worksheet.write(row, 1, token.weightment_in_datetime or ' ', date_format)
                                    worksheet.write(row, 2, token.weightment_out_datetime or ' ', date_format)
                                    worksheet.write(row, 3, bill.name, output_format)
                                    worksheet.write(row, 4, token.trailer, output_format)
                                    worksheet.write(row, 5, line.price_unit or 0.0, output_format)
                                    worksheet.write(row, 6, line.product_qty or ' ', output_format)
                                    worksheet.write(row, 7, line.qty_received or ' ', output_format)
                                    worksheet.write(row, 8, '', output_format)
                                    worksheet.write(row, 9, '', output_format)
                                    worksheet.write(row, 10, '', output_format)
                                    worksheet.write(row, 11, '', output_format)
                                    worksheet.write(row, 12, '', output_format)
                                    worksheet.write(row, 13, '', output_format)
                                    worksheet.write(row, 14, '', output_format)
                                    worksheet.write(row, 15, '', output_format)
                                    worksheet.write(row, 16, '', output_format)
                        else:
                            worksheet.write(row, 0, sr_no, output_format)
                            worksheet.write(row, 1, token.weightment_in_datetime or ' ', date_format)
                            worksheet.write(row, 2, token.weightment_out_datetime or ' ', date_format)
                            worksheet.write(row, 3, bill.name, output_format)
                            worksheet.write(row, 4, token.trailer, output_format)
                            worksheet.write(row, 5, line.price_unit or 0.0, output_format)
                            worksheet.write(row, 6, line.product_qty or ' ', output_format)
                            worksheet.write(row, 7, line.qty_received or ' ', output_format)
                            worksheet.write(row, 8, '', output_format)
                            worksheet.write(row, 9, '', output_format)
                            worksheet.write(row, 10, '', output_format)
                            worksheet.write(row, 11, '', output_format)
                            worksheet.write(row, 12, '', output_format)
                            worksheet.write(row, 13, '', output_format)
                            worksheet.write(row, 14, '', output_format)
                            worksheet.write(row, 15, '', output_format)
                            worksheet.write(row, 16, '', output_format)
            else:
                token_record = self.env['purchase.token'].search([('name_id', '=', line.order_id.id)])
                for token in token_record:
                    pickings = self.env['stock.picking'].search(
                        [('origin', '=', line.order_id.name), ('token_id', '=', token.id), ('state', '=', 'done')])
                    for pick in pickings:
                        quality_check = self.env['quality.check'].search([('picking_id', '=', pick.id)])
                        if quality_check:
                            for qc in quality_check:
                                worksheet.write(row, 0, sr_no, output_format)
                                worksheet.write(row, 1, token.weightment_in_datetime or ' ', date_format)
                                worksheet.write(row, 2, token.weightment_out_datetime or ' ', date_format)
                                worksheet.write(row, 3, '', output_format)
                                worksheet.write(row, 4, token.trailer, output_format)
                                worksheet.write(row, 5, line.price_unit or 0.0, output_format)
                                worksheet.write(row, 6, line.product_qty or ' ', output_format)
                                worksheet.write(row, 7, line.qty_received or ' ', output_format)
                                worksheet.write(row, 8, qc.starch or 0.0, output_format)
                                worksheet.write(row, 9, qc.moisture or 0.0, output_format)
                                worksheet.write(row, 10, qc.fm or 0.0, date_format)
                                worksheet.write(row, 11, ' ', output_format)
                                worksheet.write(row, 12, ' ', output_format)
                                account_move_search = self.env['account.move'].search(
                                    [('quality_check_id', '=', self.id), ('move_type', '=', 'in_refund')])

                                if account_move_search.filtered(lambda x: 'Starch' in x.ref):
                                    worksheet.write(row, 13, account_move_search.filtered(
                                        lambda x: 'Starch' in x.ref).amount or ' ', output_format)
                                else:
                                    worksheet.write(row, 13, '0.00', output_format)

                                if account_move_search.filtered(lambda x: 'Moisture' in x.ref):
                                    worksheet.write(row, 14, account_move_search.filtered(
                                        lambda x: 'Moisture' in x.ref).amount or ' ', output_format)
                                else:
                                    worksheet.write(row, 14, '0.00', output_format)

                                if account_move_search.filtered(lambda x: 'Foreign matter' in x.ref):
                                    worksheet.write(row, 15, account_move_search.filtered(
                                        lambda x: 'Foreign matter' in x.ref).amount or ' ', output_format)
                                else:
                                    worksheet.write(row, 15, '0.00', output_format)

                                worksheet.write(row, 16, ' ', output_format)

                        else:
                            worksheet.write(row, 0, sr_no, output_format)
                            worksheet.write(row, 1, token.weightment_in_datetime or ' ', date_format)
                            worksheet.write(row, 2, token.weightment_out_datetime or ' ', date_format)
                            worksheet.write(row, 3, '', output_format)
                            worksheet.write(row, 4, token.trailer, output_format)
                            worksheet.write(row, 5, line.price_unit or 0.0, output_format)
                            worksheet.write(row, 6, line.product_qty or ' ', output_format)
                            worksheet.write(row, 7, line.qty_received or ' ', output_format)
                            worksheet.write(row, 8, '', output_format)
                            worksheet.write(row, 9, '', output_format)
                            worksheet.write(row, 10, '', output_format)
                            worksheet.write(row, 11, '', output_format)
                            worksheet.write(row, 12, '', output_format)
                            worksheet.write(row, 13, '', output_format)
                            worksheet.write(row, 14, '', output_format)
                            worksheet.write(row, 15, '', output_format)
                            worksheet.write(row, 16, '', output_format)

        workbook.close()
        file_data.seek(0)
        xlsx_data = base64.encodebytes(file_data.getvalue())
        self.write({'output': xlsx_data, 'file_name': f'SAUDA' + '.xlsx'})
        file_data.close()
        return {
            'name': _('Sauda Report'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sauda.report',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
