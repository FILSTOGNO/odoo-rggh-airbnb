import logging
import requests
from odoo import models, fields, api, exceptions

_logger = logging.getLogger(__name__)

# =============================================================================
# BEDS24 INTEGRATION - STUB
# À activer quand le compte Beds24 est prêt
# Documentation API: https://beds24.com/api/v2
# =============================================================================

BEDS24_API_URL = "https://beds24.com/api/v2"

class MandaBeds24(models.Model):
    _name = 'manda.beds24'
    _description = 'Synchronisation Beds24'

    name = fields.Char(string='Nom', default='Sync Beds24')
    last_sync = fields.Datetime(string='Dernière synchro', readonly=True)
    sync_status = fields.Char(string='Statut', readonly=True, default='Non configuré')
    bookings_synced = fields.Integer(string='Réservations synchronisées', default=0)

    def _get_headers(self):
        """Obtenir les headers d'authentification Beds24"""
        settings = self.env['manda.settings'].get_settings()
        if not settings.beds24_api_key:
            raise exceptions.UserError("Clé API Beds24 non configurée dans les paramètres.")
        return {
            'token': settings.beds24_api_key,
            'Content-Type': 'application/json',
        }

    # ------------------------------------------------------------------
    # ÉTAPE 1: Tester la connexion Beds24
    # À activer quand le compte est prêt
    # ------------------------------------------------------------------
    def action_test_connection(self):
        """
        STUB - Tester la connexion à l'API Beds24
        Endpoint: GET /authentication/setup
        """
        _logger.info("BEDS24 STUB: Test connexion (à activer avec vrai compte)")
        # TODO: Décommenter quand compte Beds24 prêt
        # try:
        #     response = requests.get(
        #         f"{BEDS24_API_URL}/authentication/setup",
        #         headers=self._get_headers(),
        #         timeout=10
        #     )
        #     data = response.json()
        #     if response.status_code == 200:
        #         return self._notify_success("Connexion Beds24 réussie!")
        #     raise exceptions.UserError(f"Erreur Beds24: {data}")
        # except Exception as e:
        #     raise exceptions.UserError(f"Impossible de contacter Beds24: {e}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'STUB: Beds24 non configuré. Ajoutez votre clé API dans les paramètres.',
                'type': 'warning'
            }
        }

    # ------------------------------------------------------------------
    # ÉTAPE 2: Synchroniser les réservations depuis Beds24
    # ------------------------------------------------------------------
    def action_sync_bookings(self):
        """
        STUB - Synchroniser les réservations depuis Beds24
        Endpoint: GET /bookings
        """
        _logger.info("BEDS24 STUB: Sync réservations (à activer avec vrai compte)")
        settings = self.env['manda.settings'].get_settings()
        if not settings.beds24_sync_enabled:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Synchronisation Beds24 désactivée. Activez-la dans les paramètres.',
                    'type': 'warning'
                }
            }

        # TODO: Décommenter et adapter quand compte Beds24 prêt
        # try:
        #     response = requests.get(
        #         f"{BEDS24_API_URL}/bookings",
        #         headers=self._get_headers(),
        #         params={
        #             'arrivalFrom': fields.Date.today().strftime('%Y-%m-%d'),
        #             'includeInvoice': True,
        #         },
        #         timeout=30
        #     )
        #     bookings = response.json().get('data', [])
        #     count = 0
        #     for booking in bookings:
        #         self._process_booking(booking)
        #         count += 1
        #     self.write({'last_sync': fields.Datetime.now(), 'bookings_synced': count})
        #     settings.beds24_last_sync = fields.Datetime.now()
        # except Exception as e:
        #     _logger.error(f"Erreur sync Beds24: {e}")
        #     raise exceptions.UserError(f"Erreur synchronisation: {e}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'STUB: Synchronisation Beds24 non active. À configurer.',
                'type': 'info'
            }
        }

    # ------------------------------------------------------------------
    # ÉTAPE 3: Traiter une réservation Beds24 → Odoo
    # ------------------------------------------------------------------
    def _process_booking(self, booking_data):
        """
        Convertir une réservation Beds24 en réservation Odoo
        Structure Beds24 bookings: https://beds24.com/api/v2#tag/Bookings
        """
        # Mapper le canal Beds24 → canal Odoo
        channel_map = {
            'airbnb': 'airbnb',
            'bookingcom': 'booking',
            'direct': 'direct',
        }
        beds24_channel = booking_data.get('channel', 'direct').lower()
        odoo_channel = channel_map.get(beds24_channel, 'other')

        # Chercher ou créer le client
        partner = self._get_or_create_partner(booking_data.get('guestFirstName', ''),
                                               booking_data.get('guestLastName', ''),
                                               booking_data.get('guestEmail', ''))

        # Chercher la chambre par beds24_room_id
        room_id = booking_data.get('roomId')
        room = self.env['manda.room'].search([('beds24_room_id', '=', str(room_id))], limit=1)
        if not room:
            _logger.warning(f"Chambre Beds24 {room_id} non trouvée dans Odoo")
            return None

        # Créer ou mettre à jour la réservation
        existing = self.env['manda.reservation'].search([
            ('beds24_booking_id', '=', str(booking_data.get('bookId')))
        ], limit=1)

        vals = {
            'partner_id': partner.id,
            'room_id': room.id,
            'checkin_date': booking_data.get('arrival'),
            'checkout_date': booking_data.get('departure'),
            'channel': odoo_channel,
            'beds24_booking_id': str(booking_data.get('bookId')),
            'beds24_sync_date': fields.Datetime.now(),
            'amount_paid': booking_data.get('totalAmount', 0),
        }

        if existing:
            existing.write(vals)
            return existing
        else:
            return self.env['manda.reservation'].create(vals)

    def _get_or_create_partner(self, first_name, last_name, email):
        """Créer ou retrouver un contact client"""
        if email:
            partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
            if partner:
                return partner
        full_name = f"{first_name} {last_name}".strip() or 'Client Inconnu'
        return self.env['res.partner'].create({
            'name': full_name,
            'email': email,
            'customer_rank': 1,
        })

    # ------------------------------------------------------------------
    # WEBHOOK - Recevoir les notifications Beds24 en temps réel
    # ------------------------------------------------------------------
    # Le webhook Beds24 envoie des notifications à:
    # https://votre-odoo.com/beds24/webhook
    # À configurer dans Beds24: Settings → Notifications → Webhook
    # ------------------------------------------------------------------
