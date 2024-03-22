{
    "name": "TZT Token",
    "category": "token",
    'description': "Token",
    "author": "Planet Odoo",
    "version": "17.0.1.0.0",
    "depends": ["base","purchase","sale","sale_management","stock",'hc_transport'],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/token_type.xml",
        "views/trailer_type.xml",
        "views/reject_name.xml",
        "wizard/reject_reason.xml",
        "report/inward_token_report.xml",
        "report/inward_token_weightship_report.xml",
        "report/sale_order_report.xml",
        "report/invoice_tax_report.xml",
        "report/sale_token_report.xml",
        "views/custome_onhold.xml",
        "wizard/on_hold.xml",
        "wizard/so_token_reject.xml",
        "views/purchase_order.xml",
        "views/purchase_token.xml",
        "views/sale_token.xml",
        "views/product.xml",
        "views/sale.xml",
        "views/main_menu.xml",
        'views/stock_picking.xml',


    ],
    "qweb": [],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",

}

