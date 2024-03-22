import werkzeug
import json
import base64
import odoo.http as http
from odoo.http import request

token_structure = {
	'sale' : 'sale.token',
	'purchase' : 'purchase.token'
}
class CreateToken(http.Controller):

    @http.route('/get/token', type='json', auth="public")
    def update_weight(self, **kw):
        try:
            token = request.env[token_structure[kw.get('type')]].search([('name', '=', kw.get('TicketNo'))])
            result = token.get_token_data(kw)
            response = {
                'Start': "Success", 
				'Error':[], 
				'Output': result 
            }

        except Exception as e:
            response = {
                'Start': "FAILED",
                'Error': [str(e)],
                'Output': result,
            }
        return response

class UpdateToken(http.Controller):

    @http.route('/update/token', type='json', auth="public")
    def update_weight(self, **kw):
        try:
            token = request.env[token_structure[kw.get('type')]].search([('name', '=', kw.get('TicketNo'))])
            result = token.update_token_data(kw)

            response = {
                'Start': "Success", 
				'Error':[], 
				'Output': result 
            }

        except Exception as e:
            response = {
                'Start': "FAILED",
                'Error': [str(e)],
                'Output': result,  
            }
        return response

