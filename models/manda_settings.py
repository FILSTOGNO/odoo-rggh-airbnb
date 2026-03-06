from odoo import models, fields, api

class MandaSettings(models.Model):
    _name = 'manda.settings'
    _description = 'Configuration Airbnb_Manda'
    _rec_name = 'name'

    name = fields.Char(default='Configuration Airbnb_Manda', readonly=True)

    # UniFi Access
    unifi_api_token = fields.Char(string='Token API UniFi')
    unifi_hub_ip = fields.Char(string='IP Gateway VLAN MANDA-Porte', default='172.18......')
    unifi_switch_ip = fields.Char(string='IP Switch principal (USW-01)', default='172.30......')
    unifi_switch2_ip = fields.Char(string='IP Switch secondaire (USW-02)', default='172.30......')

    # Beds24
    beds24_api_key = fields.Char(string='Clé API Beds24')
    beds24_refresh_token = fields.Char(string='Refresh Token Beds24')
    beds24_sync_enabled = fields.Boolean(string='Synchronisation Beds24 activée', default=False)
    beds24_last_sync = fields.Datetime(string='Dernière synchronisation', readonly=True)

    # Compte bancaire
    bank_account = fields.Char(string='IBAN / Numéro de compte')
    bank_name = fields.Char(string='Nom de la banque')
    bank_bic = fields.Char(string='BIC / SWIFT')

    # Email et PIN
    email_from = fields.Char(string='Email expéditeur')
    pin_length = fields.Integer(string='Longueur du code PIN', default=4)
    auto_send_pin = fields.Boolean(string='Envoi automatique du PIN', default=True)

    # Facturation
    auto_invoice = fields.Boolean(string='Facturation automatique', default=False)
    invoice_journal_id = fields.Many2one('account.journal', string='Journal de facturation')

    @api.model
    def get_settings(self):
        settings = self.search([], limit=1)
        if not settings:
            settings = self.create({'name': 'Configuration Airbnb_Manda'})
        return settings