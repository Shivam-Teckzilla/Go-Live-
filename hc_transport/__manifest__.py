{
    "name": " TZT Transport",
    "category": "Transport",
    'description': "Transport",
    "author": "Planet Odoo",
    "version": "17.0.1.0.0",
    "depends": ["base","purchase","approvals","sale_management","stock","sale_stock","sale","purchase_stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/approval_cat.xml",
        "data/ir_sequence.xml",
        "views/transport.xml",
        "views/res_partner.xml",
        "views/trasporter_rates.xml",
        "views/customer_rate.xml",
        "views/tbs_sale.xml",
        "views/tbs_purchase.xml",
        "views/transport_menu.xml",
        "views/approval_cat.xml",
        "views/product_template.xml",
        "wizard/stock_picking_wizard.xml",



    ],
    "qweb": [],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",

}

