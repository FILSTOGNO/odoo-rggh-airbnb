import requests
import logging
from odoo import models, fields, api, exceptions

_logger = logging.getLogger(__name__)


class MandaLock(models.Model):
    _name = 'manda.lock'
    _description = 'Serrure UniFi Access'
    _rec_name = 'name'

    name = fields.Char(string='Nom', required=True)
    door_id = fields.Char(string='ID Porte UniFi', required=True)
    access_policy_id = fields.Char(
        string='Access Policy ID',
        default='d1596c28-.................682f'
    )
    active = fields.Boolean(default=True)
    room_id = fields.One2many('manda.room', 'lock_id', string='Chambre')

    def _get_base_url(self):
        settings = self.env['manda.settings'].get_settings()
        if not settings or not settings.unifi_hub_ip:
            raise exceptions.UserError("IP du hub UniFi non configuree.")
        return f"http://{settings.unifi_hub_ip}:12445"

    def _get_headers(self):
        settings = self.env['manda.settings'].get_settings()
        if not settings or not settings.unifi_api_token:
            raise exceptions.UserError("Token API UniFi non configure.")
        return {
            'Authorization': f'Bearer {settings.unifi_api_token}',
            'Content-Type': 'application/json',
        }

    def _api_request(self, method, endpoint, data=None):
        url = f"{self._get_base_url()}{endpoint}"
        try:
            resp = requests.request(
                method, url,
                headers=self._get_headers(),
                json=data, verify=False, timeout=10
            )
            return resp.json()
        except Exception as e:
            _logger.error(f"Erreur API UniFi: {e}")
            raise exceptions.UserError(f"Impossible de contacter le hub UniFi: {e}")

    def _find_existing_user(self, email):
        result = self._api_request('GET', '/api/v1/developer/users')
        if result.get('code') == 'SUCCESS':
            for user in result.get('data', []):
                if user.get('user_email') == email or user.get('email') == email:
                    _logger.info(f"Utilisateur UniFi existant trouve: {user['id']}")
                    return user['id']
        return None

    def create_unifi_user(self, first_name, last_name, email, pin_code, start_time, end_time):
        user_id = self._find_existing_user(email)
        if not user_id:
            data = {
                "first_name": first_name,
                "last_name": last_name,
                "user_email": email,
                "onboard_time": int(start_time.timestamp()) if start_time else 0,
            }
            result = self._api_request('POST', '/api/v1/developer/users', data)
            if result.get('code') != 'SUCCESS':
                _logger.error(f"Erreur creation user UniFi: {result}")
                return None
            user_id = result['data']['id']
            _logger.info(f"Nouvel utilisateur UniFi cree: {user_id}")
        self._api_request('PUT', f'/api/v1/developer/users/{user_id}/pin_codes', {"pin_code": pin_code})
        self._api_request('PUT', f'/api/v1/developer/users/{user_id}/access_policies', {
            "access_policy_id": self.access_policy_id,
            "start_time": int(start_time.timestamp()) if start_time else 0,
            "end_time": int(end_time.timestamp()) if end_time else 0,
        })
        _logger.info(f"Acces UniFi configure: {user_id}")
        return user_id

    def delete_unifi_user(self, user_id):
        result = self._api_request('DELETE', f'/api/v1/developer/users/{user_id}')
        if result.get('code') == 'SUCCESS':
            _logger.info(f"Utilisateur UniFi supprime: {user_id}")
            return True
        return False

    def test_connection(self):
        result = self._api_request('GET', '/api/v1/developer/users')
        if result.get('code') == 'SUCCESS':
            count = len(result.get('data', []))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': f'Connexion UniFi reussie! {count} utilisateurs.', 'type': 'success'}
            }
        raise exceptions.UserError(f"Echec connexion: {result}")