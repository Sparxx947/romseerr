#!/bin/sh
# Zertifikat holen und frisch halten. Läuft im certbot-Beiwagen. / Obtain and renew.
#
# Warum ein eigenes Skript und nicht bloss `certbot renew`: certbot erneuert nur in
# SEINEM Volume. Der Streaming-Host liest aber /config/ssl/cert.pem — die Kopie muss
# also mit. Sonst läuft das Zertifikat im Container ab, obwohl certbot längst
# erneuert hat, und niemand merkt es bis zum Ablauftag.
#
# certbot renew alone only updates certbot's own volume; the streaming host reads
# from elsewhere. Without copying, the served certificate silently goes stale.
set -u

DOM="${CERT_DOMAIN}"
LIVE="/etc/letsencrypt/live/${DOM}"
PLUGIN="${DNS_PLUGIN:-cloudflare}"
PROP="${PROPAGATION_SECONDS:-30}"

# Die Zugangsdatei muss 600 sein, sonst weigert sich certbot. Sie kommt read-only
# herein, deshalb eine private Kopie. / certbot refuses world-readable credentials;
# the mount is read-only, so work on a private copy.
cp /creds/dns.ini /tmp/dns.ini
chmod 600 /tmp/dns.ini

install_cert() {
  [ -f "${LIVE}/fullchain.pem" ] || return 1
  cp -L "${LIVE}/fullchain.pem" /ssl/cert.pem
  cp -L "${LIVE}/privkey.pem"   /ssl/cert.key
  chown "${OWNER_UID:-1000}:${OWNER_GID:-1000}" /ssl/cert.pem /ssl/cert.key 2>/dev/null
  chmod 644 /ssl/cert.pem
  chmod 600 /ssl/cert.key
  echo "[$(date '+%F %T')] Zertifikat nach /ssl gelegt / certificate installed"
}

while true; do
  if [ -d "${LIVE}" ]; then
    certbot renew --quiet \
      "--dns-${PLUGIN}" "--dns-${PLUGIN}-credentials" /tmp/dns.ini \
      "--dns-${PLUGIN}-propagation-seconds" "${PROP}"
  else
    echo "[$(date '+%F %T')] Erstausstellung für ${DOM} / first issuance"
    certbot certonly --non-interactive --agree-tos --no-eff-email \
      -m "${CERT_EMAIL}" -d "${DOM}" \
      "--dns-${PLUGIN}" "--dns-${PLUGIN}-credentials" /tmp/dns.ini \
      "--dns-${PLUGIN}-propagation-seconds" "${PROP}"
  fi

  # Immer kopieren, auch wenn certbot nichts getan hat: der Wächter im Streaming-Host
  # lädt ohnehin nur bei GEÄNDERTEM Fingerabdruck neu, ein Kopieren kostet nichts.
  # Copy unconditionally; the watcher only reloads when the fingerprint changes.
  install_cert || echo "[$(date '+%F %T')] noch kein Zertifikat / none yet"

  echo "[$(date '+%F %T')] schlafe ${RENEW_INTERVAL:-43200} s / sleeping"
  sleep "${RENEW_INTERVAL:-43200}"
done
