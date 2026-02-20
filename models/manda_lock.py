import requests
import logging
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)

class MandaLock(models.Model):
    _name = 'manda.lock'
    _description = 'Serrure UniFi Access'
    _rec_name = 'name'

    name = fields.Char(string='Nom de la serrure', required=True)
    door_location_id = fields.Char(string='Location ID UniFi', help='ID de la porte dans UniFi Access via GET /api/v1/developer/locations')
    access_policy_id = fields.Char(string='Access Policy ID', help='ID de la politique d\'accès UniFi à appliquer aux clients.')
    room_id = fields.One2many('manda.room', 'lock_id', string='Chambre associée')
    state = fields.Selection([
        ('unknown', 'Inconnu'),
        ('online', 'En ligne'),
        ('offline', 'Hors ligne'),
    ], string='État', default='unknown')
    last_sync = fields.Datetime(string='Dernière synchronisation')
    notes = fields.Text(string='Notes')

    def _get_headers(self):
        settings = self.env['manda.settings'].sudo().get_settings()
        if not settings or not settings.unifi_api_token:
            raise exceptions.UserError("Token API UniFi non configuré.")
        return {
            'Authorization': f"Bearer {settings.unifi_api_token}",
            'Content-Type': 'application/json',
        }

    def _get_base_url(self):
        settings = self.env['manda.settings'].sudo().get_settings()
        if not settings or not settings.unifi_hub_ip:
            raise exceptions.UserError("IP du hub UniFi non configurée.")
        return f"https://{settings.unifi_hub_ip}:12445"

    def _api_request(self, method, endpoint, data=None):
        url = f"{self._get_base_url()}{endpoint}"
        try:
            response = requests.request(method, url, headers=self._get_headers(), json=data, verify=False, timeout=10)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.ConnectionError:
            raise exceptions.UserError(f"Impossible de contacter le hub UniFi à {self._get_base_url()}.")
        except requests.exceptions.HTTPError as e:
            raise exceptions.UserError(f"Erreur API UniFi ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            raise exceptions.UserError(f"Erreur inattendue: {str(e)}")

    def create_temp_user(self, reservation):
        name_parts = (reservation.partner_id.name or 'Client').split()
        payload = {
            "first_name": name_parts[0],
            "last_name": name_parts[-1] if len(name_parts) > 1 else "Client",
            "email": reservation.partner_email or "",
            "employee_number": reservation.reference,
            "onboard_time": int(reservation.checkin_date.timestamp()),
        }
        result = self._api_request('POST', '/api/v1/developer/users', payload)
        user_id = result.get('data', {}).get('id')
        if not user_id:
            raise exceptions.UserError(f"Impossible de créer l'utilisateur UniFi. Réponse: {result}")
        _logger.info(f"Utilisateur UniFi créé: {user_id} pour {reservation.reference}")
        return user_id

    def assign_pin_to_user(self, unifi_user_id, pin):
        result = self._api_request('PUT', f'/api/v1/developer/users/{unifi_user_id}', {"pin_code": pin})
        _logger.info(f"PIN assigné à {unifi_user_id}")
        return result

    def assign_access_policy(self, unifi_user_id, reservation):
        if not self.access_policy_id:
            _logger.warning(f"Serrure {self.name}: access_policy_id non défini.")
            return False
        payload = {
            "access_policies": [{
                "policy_id": self.access_policy_id,
                "start_time": int(reservation.checkin_date.timestamp()),
                "end_time": int(reservation.checkout_date.timestamp()),
            }]
        }
        return self._api_request('PUT', f'/api/v1/developer/users/{unifi_user_id}', payload)

    def delete_temp_user(self, unifi_user_id):
        try:
            self._api_request('DELETE', f'/api/v1/developer/users/{unifi_user_id}')
            _logger.info(f"Utilisateur UniFi {unifi_user_id} supprimé.")
            return True
        except Exception as e:
            _logger.error(f"Erreur suppression {unifi_user_id}: {e}")
            return False

    def create_unifi_access(self, pin, start_time, end_time, label='', reservation=None):
        self.ensure_one()
        if not reservation:
            return False
        unifi_user_id = self.create_temp_user(reservation)
        self.assign_pin_to_user(unifi_user_id, pin)
        self.assign_access_policy(unifi_user_id, reservation)
        self.last_sync = fields.Datetime.now()
        self.state = 'online'
        return unifi_user_id

    def revoke_unifi_access(self, pin=None, unifi_user_id=None):
        self.ensure_one()
        if not unifi_user_id:
            return False
        return self.delete_temp_user(unifi_user_id)

    def action_unlock_door(self):
        self.ensure_one()
        if not self.door_location_id:
            raise exceptions.UserError("Location ID de la porte non configuré.")
        self._api_request('PUT', f'/api/v1/developer/doors/{self.door_location_id}/unlock')
        self.state = 'online'
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Porte déverrouillée', 'message': f'La porte {self.name} a été déverrouillée.', 'type': 'success'}}

    def action_test_connection(self):
        self.ensure_one()
        result = self._api_request('GET', '/api/v1/developer/users?page_num=1&page_size=1')
        count = result.get('data', {}).get('total_count', '?')
        self.state = 'online'
        self.last_sync = fields.Datetime.now()
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '✅ Connexion réussie', 'message': f'Hub UniFi accessible. {count} utilisateur(s).', 'type': 'success'}}
