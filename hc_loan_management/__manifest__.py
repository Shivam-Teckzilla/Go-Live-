# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "TZT Loan Management",
    "version" : "17.0.0.0",
    "category" : "Sales",
    'summary': 'Customer loan Management',
    "description": """Loan Management
    """,
    "author": "Tackzilla Tech.",
    "website" : "",
    "price": 22,
    "currency": 'EUR',
    "depends" : ['base','hr', 'account', 'hr_contract_types', 'approvals' ],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/hr_loan_view.xml',
        'views/hr_contract_view.xml',
    ],
    "license":'OPL-1',
    'qweb': [
    ],
    "auto_install": False,
    "installable": True,
    "live_test_url":'https://youtu.be/Uxc5jQPglYY',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
