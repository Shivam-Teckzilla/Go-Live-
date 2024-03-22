from odoo import models, api
from datetime import datetime



class sales_margin_report(models.AbstractModel):
    _name = 'report.vendor_reporting.purchase_order_template'
    _description="Purchase Report"

    
    
    def _get_report_values(self, docids, data=None):
        PurchaseOrder = self.env['account.move']

        domain = [('move_type', '=', 'in_invoice')]
        if data.get('start_date'):
            domain.append(('date', '>=', data['start_date']))
        if data.get('end_date'):
            domain.append(('date', '<=', data['end_date']))

        if data.get('selected') and data.get('vendor_ids'):
            domain.append(('partner_id', 'in', data['vendor_ids']))
        elif not data.get('selected'):
            domain.append(('partner_id', '!=', False))

        purchase_orders = PurchaseOrder.search(domain)

        report_data = {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'data': data,
            'purchase_orders': [],
        }

        for order in purchase_orders:
            if any(line.purchase_order_id for line in order.invoice_line_ids if line.purchase_order_id):
                report_data['purchase_orders'].append(order)

        return report_data