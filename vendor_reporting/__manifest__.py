# -*- coding: utf-8 -*-

{
    'name': 'TZT Custom Purchase Order Report',
    'version': '17.0.0.0',
    'category': 'purchase',
    'summary': """
        Custom Purchase Order Report
    """,
    'description': """Custom Purchase Order Reportin""",
    'author': 'Teckzilla Tech',
    'company': 'Teckzilla Tech',
    'maintainer': 'Teckzilla Tech',
    'website': 'https://www.cybrosys.com',
    'depends': ['hr', 'purchase','hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/employee.xml',
        'views/sauda_report_view.xml',
        'wizard/purchase_order_wizard.xml',
        'report/purchase_order_vendor_report.xml',
        'report/report_views.xml',
        'report/empolyee_pdf_report.xml',
        'report/purchase_voucher_report.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}