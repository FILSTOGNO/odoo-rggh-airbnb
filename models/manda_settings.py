from odoo import models, fields, api

class MandaSettings(models.Model):
    _name = 'manda.settings'
    _description = 'Configuration MandaBar UniFi'
    _rec_name = 'name'

    name = fields.Char(default='Configuration MandaBar', readonly=True)
    unifi_api_token = fields.Char(string='Token API UniFi', help='Token Bearer pour l\'API UniFi Access.')
    unifi_hub_ip = fields.Char(string='IP Enterprise Access Hub', default='172.18.244.254')
    unifi_switch_ip = fields.Char(string='IP Switch principal (USW-01)', default='172.18.244.254')
    unifi_switch2_ip = fields.Char(string='IP Switch secondaire (USW-02)', default='172.30.69.80')
    bank_account = fields.Char(string='IBAN / Numéro de compte')
    bank_name = fields.Char(string='Nom de la banque')
    bank_bic = fields.Char(string='BIC / SWIFT')
    email_from = fields.Char(string='Email expéditeur')
    pin_length = fields.Integer(string='Longueur du code PIN', default=4)
    auto_send_pin = fields.Boolean(string='Envoi automatique du PIN', default=True)

    @api.model
    def get_settings(self):
        settings = self.search([], limit=1)
        if not settings:
            settings = self.create({'name': 'Configuration MandaBar'})
        return settings
