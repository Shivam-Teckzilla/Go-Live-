{
    "name": "TZT HC Accounting",
    "category": "Token",
    'description': "Token",
    "author": "Planet Odoo",
    "version": "17.0.1.0.0",
    "depends": ["base","purchase","sale","account","sale_management","stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        'views/account_tax.xml',


    ],
    "qweb": [],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",

}

