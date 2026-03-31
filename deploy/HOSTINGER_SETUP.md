# Guía de Deploy en Hostinger VPS

## Requisitos
- Hostinger VPS con Ubuntu 22.04
- Python 3.10+
- Nginx (se instala abajo)

---

## Paso 1 — Subir el ZIP

En el panel de Hostinger → **File Manager**, sube `polymarket-arb-bot.zip` a `/root/`.

O desde la terminal SSH:
```bash
scp polymarket-arb-bot.zip root@TU_IP:/root/
```

---

## Paso 2 — Descomprimir y configurar

```bash
ssh root@TU_IP

cd /root
unzip polymarket-arb-bot.zip
mv Oskarcompains polymarket-arb-bot
cd polymarket-arb-bot

# Crear tu archivo de credenciales
cp .env.example .env
nano .env
# → Pega tu POLYMARKET_PRIVATE_KEY, POLYMARKET_FUNDER, etc.

mkdir -p logs
```

---

## Paso 3 — Instalar dependencias

```bash
apt update && apt install -y python3-pip nginx
pip3 install -r requirements.txt
```

---

## Paso 4 — Nginx

```bash
# Editar el dominio en el config
sed -i 's/TUDOMINIO.COM/tudominio.com/g' deploy/nginx.conf

cp deploy/nginx.conf /etc/nginx/sites-available/polymarket-bot
ln -sf /etc/nginx/sites-available/polymarket-bot /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

## Paso 5 — SSL gratuito (Let's Encrypt)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d tudominio.com -d www.tudominio.com
# Descomenta el bloque HTTPS en deploy/nginx.conf y recarga nginx
```

---

## Paso 6 — Arrancar el bot como servicio (se reinicia solo)

```bash
# Ajusta la ruta si es diferente
sed -i 's|/root/polymarket-arb-bot|'$(pwd)'|g' deploy/polymarket-bot.service

cp deploy/polymarket-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable polymarket-bot
systemctl start polymarket-bot

# Ver estado
systemctl status polymarket-bot

# Ver logs en vivo
tail -f logs/service.log
```

---

## Resultado

- **Dashboard**: `https://tudominio.com`
- **API docs**: `https://tudominio.com/api/docs`

---

## Comandos útiles

```bash
systemctl stop polymarket-bot     # Parar
systemctl restart polymarket-bot  # Reiniciar
journalctl -u polymarket-bot -f   # Logs del sistema
```
