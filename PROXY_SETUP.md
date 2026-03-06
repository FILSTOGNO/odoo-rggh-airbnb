# 🔒 Airbnb_Manda — Proxy UniFi Access

> Documentation technique du proxy permettant à Odoo (VPS OVH) de communiquer  
> avec le hub UniFi Access situé sur le réseau local de l'établissement.
>
> * • Mars 2026 • Angelbert FANKEP*

---

## 🧩 Pourquoi un Proxy ?

Un proxy est un intermédiaire qui relaie les communications entre deux systèmes qui ne peuvent pas se parler directement.

| ❌ Sans Proxy | ✅ Avec Proxy |
|---|---|
| Odoo (VPS Internet) | Odoo (VPS Internet) |
| ↓ | ↓ tunnel SSH |
| ❌ Impossible | Raspberry Pi (bridge) |
| ↓ | ↓ réseau local |
| UniFi Hub (réseau local) | UniFi Hub ✅ |

> 💡 **Le Raspberry Pi agit comme un pont** : il est à la fois sur Internet (via SSH) et sur le réseau local de l'établissement (via Wi-Fi/Ethernet).

---

## 🏗️ Architecture Complète

```
┌─────────────────────────────────────────────────────────────┐
│                    RÉSEAU LOCAL MandaBar                    │
│                                                             │
│  ┌──────────────────────┐      ┌────────────────────────┐  │
│  │  UniFi Access Hub    │◄────►│   Raspberry Pi          │  │
│  │  172.18.x.x          │ LAN  │   172.18.x.x            │  │
│  │  Port: 12445         │      │   Flask proxy: 8445     │  │
│  └──────────────────────┘      └───────────┬────────────┘  │
│                                            │               │
└────────────────────────────────────────────┼───────────────┘
                                             │ Tunnel SSH inversé
                                             │ (-R 12445:localhost:8445)
                                             │
                                ┌────────────▼────────────────┐
                                │     VPS OVH                 │
                                │     vps213949.ovh.net       │
                                │                             │
                                │  localhost:12445 ───────────┼──► Hub UniFi
                                │                             │
                                │  Odoo 19 (port 8069)        │
                                │  PostgreSQL                 │
                                └─────────────────────────────┘
```

### Composants

| Composant | Adresse                | Rôle |
|---|------------------------|---|
| **Odoo (VPS OVH)** | vps213949.ovh.net:8069 | Interface web, gestion des réservations |
| **Raspberry Pi** | 172.18.x.x             | Proxy bridge — tunnel SSH + Flask proxy |
| **UniFi Access Hub** | 172.18.x.x:12445     | Gestion des serrures et codes PIN |
| **Serrures / Portes** | Via UniFi Hub          | Déverrouillage physique des chambres |

---

## 📁 Fichiers du Projet

### 3.1 `unifi_proxy.py` — Script Flask (Raspberry Pi)

Ce script Python tourne en permanence sur le Raspberry Pi.  
Il écoute sur le port **8445** et relaie toutes les requêtes vers le Hub UniFi.

```python
# ── CONFIGURATION ──────────────────────────────────────────
UNIFI_HUB_IP   = "172.18.x.x"  # IP UniFi Access Hub
UNIFI_HUB_PORT = 12445             # Port API UniFi Access
PROXY_PORT     = 8445              # Port d'écoute local sur le Raspberry Pi

# ── ENDPOINT PRINCIPAL ──────────────────────────────────────
@app.route('/api/v1/developer/<path:endpoint>',
           methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(endpoint):
    # Relaie la requête vers UniFi Hub
    target = f"https://{UNIFI_HUB_IP}:{UNIFI_HUB_PORT}/api/v1/developer/{endpoint}"
    resp = requests.request(method, target, headers=headers, verify=False)
    return Response(resp.content, status=resp.status_code)
```

📁 Emplacement : `/home/angelbert/unifi_proxy/unifi_proxy.py`

---

### 3.2 `unifi_proxy.service` — Service systemd (Raspberry Pi)

Démarre automatiquement le proxy Flask au boot du Raspberry Pi.

```ini
[Unit]
Description=UniFi Access Proxy (Flask)
After=network.target

[Service]
Type=simple
User=angelbert
WorkingDirectory=/home/angelbert/unifi_proxy
ExecStart=/home/angelbert/unifi_proxy/venv/bin/python3 \
          /home/angelbert/unifi_proxy/unifi_proxy.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

📁 Emplacement : `/etc/systemd/system/unifi_proxy.service`

---

### 3.3 `ssh_tunnel.service` — Service systemd (Raspberry Pi)

Crée automatiquement le tunnel SSH inversé entre le Raspberry Pi et le VPS OVH au boot.

```ini
[Unit]
Description=Tunnel SSH Inversé vers VPS OVH
After=network-online.target

[Service]
Type=simple
User=angelbert
ExecStart=/usr/bin/ssh -N \
  -R 12445:localhost:8445 \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o StrictHostKeyChecking=no \
  -i /home/angelbert/.ssh/id_ed25519 \
  openerp@vps213949....             # openerp@vps213949.... est le serveur odoo sur lequel ce trouve le modul API
Restart=always
RestartSec=15
```

📁 Emplacement : `/etc/systemd/system/ssh_tunnel.service`

> 💡 `-R 12445:localhost:8445` signifie : le port **12445 du VPS** est redirigé vers le port **8445 du Raspberry Pi**.

---

## ⚙️ Guide d'Installation

### Étape 1 — Générer la clé SSH sur le Raspberry Pi

Cette clé permet au Raspberry Pi de se connecter au VPS sans mot de passe.

```bash
ssh-keygen -t ed25519 -C "unifi-proxy" \
  -f /home/angelbert/.ssh/id_ed25519 -N ""

# Afficher la clé publique (à copier pour l'étape 2)
cat /home/angelbert/.ssh/id_ed25519.pub
```

📋 Copiez la ligne commençant par `ssh-ed25519` — vous en aurez besoin à l'étape suivante.

---

### Étape 2 — Autoriser la clé SSH sur le VPS

```bash
# Sur le VPS OVH
echo "ssh-ed25519 AAAA... unifi-proxy" \
  >> /home/openerp/.ssh/authorized_keys

chmod 600 /home/openerp/.ssh/authorized_keys
```

---

### Étape 3 — Installer le proxy Flask sur le Raspberry Pi

```bash
mkdir -p /home/angelbert/unifi_proxy
cd /home/angelbert/unifi_proxy

# Créer l'environnement virtuel Python
python3 -m venv venv
venv/bin/pip install flask requests

# Copier le script proxy
nano /home/angelbert/unifi_proxy/unifi_proxy.py
```

---

### Étape 4 — Installer les services systemd

```bash
# Créer les fichiers service
sudo nano /etc/systemd/system/unifi_proxy.service
sudo nano /etc/systemd/system/ssh_tunnel.service

# Activer et démarrer les deux services
sudo systemctl daemon-reload
sudo systemctl enable unifi_proxy ssh_tunnel
sudo systemctl start unifi_proxy ssh_tunnel
```

---

### Étape 5 — Vérifier que tout fonctionne

```bash
# Sur le Raspberry Pi
sudo systemctl status unifi_proxy ssh_tunnel
curl http://127.0.0.1:8445/health

# Sur le VPS
curl http://127.0.0.1:12445/health
# Doit retourner : {"status": "ok", "proxy": "RPi → 172.18.x.x:12445"}
```

---

### Étape 6 — Configurer Odoo

Dans l'interface Odoo → **MandaBar → Configuration** :

| Paramètre | ❌ Avant (direct) | ✅ Après (via tunnel) |
|---|---|---|
| IP Gateway | 172.18.x.x | 127.0.0.1 |
| Port | 12445 | 12445 |

---

## 🔄 Commandes Utiles

```bash
# Vérifier les services
sudo systemctl status unifi_proxy
sudo systemctl status ssh_tunnel

# Voir les logs du proxy en temps réel
tail -f /home/angelbert/unifi_proxy/proxy.log

# Redémarrer les services
sudo systemctl restart unifi_proxy ssh_tunnel

# Vérifier le tunnel depuis le VPS
ss -tlnp | grep 12445
curl http://127.0.0.1:12445/health

# Tester l'API UniFi directement depuis le Raspberry Pi
curl -sk https://172.18.x.x:12445/api/v1/developer/users \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

---

## 🐛 Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| Tunnel ne se connecte pas | Pas d'accès internet | Vérifier la connexion Wi-Fi du Raspberry Pi |
| Port 12445 non disponible sur VPS | Tunnel coupé | `sudo systemctl restart ssh_tunnel` |
| API UniFi timeout | Hub éteint ou injoignable | Vérifier que le hub est allumé sur le LAN |
| Flask proxy ne répond pas | Service arrêté | `sudo systemctl restart unifi_proxy` |
| Erreur 502 dans Odoo | Tunnel + proxy non actifs | Redémarrer les deux services |

> ⚠️ Si le tunnel se déconnecte, il **redémarre automatiquement** grâce à `Restart=always` dans le service systemd.

---

## 👨‍💻 Auteur

**Angelbert FANKEP**  
Bachelor Informatique Industrielle — Institut de technologie de Liège (2026)

- 🌐 [fankepa.com](https://fankepa.com)
- 💼 [GitHub](https://github.com/FILSTOGNO)

---

