import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class MandaController(http.Controller):

    @http.route('/beds24/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def beds24_webhook(self, **kwargs):
        """
        STUB - Webhook pour recevoir les notifications Beds24 en temps réel
        À configurer dans Beds24: Settings → API → Webhook URL
        URL: https://votre-domaine/beds24/webhook
        """
        try:
            data = json.loads(request.httprequest.data)
            _logger.info(f"Beds24 webhook reçu: {data}")
            # TODO: Traiter la notification Beds24
            # booking_id = data.get('bookId')
            # if booking_id:
            #     sync = request.env['manda.beds24'].sudo()
            #     sync._process_booking(data)
            return {'status': 'ok'}
        except Exception as e:
            _logger.error(f"Erreur webhook Beds24: {e}")
            return {'status': 'error', 'message': str(e)}
