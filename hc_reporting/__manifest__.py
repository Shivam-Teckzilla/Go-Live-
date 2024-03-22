# -*- coding: utf-8 -*-

{
    'name': 'TZT Custom Purchase Order Report',
    'version': '17.0.0.0',
    'category': 'purchase',
    'summary': """
        Custom Purchase Order Reportin
    """,
    'description': """Custom Purchase Order Reportin""",
    'author': 'Teckzilla Tech',
    'company': 'Teckzilla Tech',
    'maintainer': 'Teckzilla Tech',
    'website': 'https://www.cybrosys.com',
    'depends': ['hr', 'purchase','hr', 'sale_management', 'account', 'base', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/employee.xml',
        'views/sale_order.xml',

        'wizard/purchase_order_wizard.xml',
        'wizard/account_move_wizard.xml',
        'wizard/report_vendor_wizard.xml',
        'report/purchase_order_vendor_report.xml',
        'report/report_views.xml',
        'report/empolyee_pdf_report.xml',
        'report/purchase_voucher_report.xml',
        'wizard/formm_wizard.xml',
        'report/tax_account_report.xml',
        'report/tax_invoice_report.xml',
        'report/purchase_tax_invoice.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}