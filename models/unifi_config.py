# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class UnifiConfig(models.Model):
    _name = 'unifi.config'
    _description = 'Configuration UniFi Access'

    name = fields.Char(string='Nom', required=True)
    api_url = fields.Char(string='URL API', default='https://172.30.69.254:12445')
    api_token = fields.Char(string='Token API')
    active = fields.Boolean(default=True)

    @api.model
    def get_active_config(self):
        return self.search([('active', '=', True)], limit=1)

    def test_connection(self):
        self.ensure_one()
        try:
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                f'{self.api_url}/api/v1/developer/users',
                headers=headers, verify=False, timeout=10
            )
            if response.status_code == 200:
                return {'type': 'ir.actions.client', 'tag': 'display_notification',
                        'params': {'message': '✅ Connexion réussie !', 'type': 'success'}}
            else:
                return {'type': 'ir.actions.client', 'tag': 'display_notification',
                        'params': {'message': f'❌ Erreur {response.status_code}', 'type': 'danger'}}
        except Exception as e:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'message': f'❌ {str(e)}', 'type': 'danger'}}
