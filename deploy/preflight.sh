#!/usr/bin/env bash
# TokenForge pre-flight check.
# Run this on the OCI VM BEFORE running oci_setup.sh to catch problems early.

set -u

API_DOMAIN="${1:-api.alreadyherellc.com}"
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; NC=$'\033[0m'
ERRORS=0; WARNINGS=0

ok()    { echo "${GREEN}✓${NC} $*"; }
warn()  { echo "${YELLOW}⚠${NC} $*"; WARNINGS=$((WARNINGS+1)); }
fail()  { echo "${RED}✗${NC} $*"; ERRORS=$((ERRORS+1)); }

echo "=== TokenForge OCI pre-flight check ==="
echo ""

# 1. Ubuntu version
if grep -q "Ubuntu 22.04" /etc/os-release 2>/dev/null; then
    ok "OS: Ubuntu 22.04"
elif grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    warn "OS: $(grep PRETTY_NAME /etc/os-release | cut -d= -f2) — script tested on 22.04, may need adjustments"
else
    fail "OS is not Ubuntu — script will not work"
fi

# 2. Root or sudo
if [ "$EUID" -eq 0 ]; then
    ok "Running as root"
else
    fail "Must run as root (or via sudo -i)"
fi

# 3. RAM + swap
RAM_MB=$(free -m | awk '/Mem:/ {print $2}')
SWAP_MB=$(free -m | awk '/Swap:/ {print $2}')
if [ "$RAM_MB" -lt 900 ]; then
    warn "Only ${RAM_MB} MB RAM — Mongo will need the 2 GB swap the setup script adds"
else
    ok "RAM: ${RAM_MB} MB"
fi
echo "  current swap: ${SWAP_MB} MB"

# 4. Disk space
FREE_GB=$(df -BG / | awk 'NR==2 {gsub("G","",$4); print $4}')
if [ "$FREE_GB" -lt 10 ]; then
    fail "Only ${FREE_GB}G free on / — need at least 10G for Mongo + Python venv"
else
    ok "Disk: ${FREE_GB}G free on /"
fi

# 5. Code present
if [ -f /opt/tokenforge/backend/server.py ]; then
    ok "Code: /opt/tokenforge/backend/server.py present"
else
    fail "Code: /opt/tokenforge/backend/server.py MISSING — clone repo to /opt/tokenforge first"
fi

# 6. .env present and filled
ENV_FILE=/opt/tokenforge/backend/.env
if [ ! -f "$ENV_FILE" ]; then
    fail ".env file missing at ${ENV_FILE}"
else
    ok ".env file exists"
    # Check no REPLACE_WITH placeholders remain
    if grep -q "REPLACE_WITH" "$ENV_FILE"; then
        fail ".env still has REPLACE_WITH placeholders — fill in real values:"
        grep -n "REPLACE_WITH" "$ENV_FILE" | sed 's/^/    /'
    else
        ok ".env has no placeholder values"
    fi
    # Required keys
    for k in MONGO_URL DB_NAME JWT_SECRET STRIPE_API_KEY GOOGLE_API_KEY RESEND_API_KEY SENDER_EMAIL CORS_ORIGINS; do
        if grep -q "^${k}=" "$ENV_FILE" && [ -n "$(grep "^${k}=" "$ENV_FILE" | cut -d= -f2- | tr -d '\"')" ]; then
            ok ".env has ${k}"
        else
            fail ".env missing or empty: ${k}"
        fi
    done
fi

# 7. DNS resolves to this server
EXPECTED_IP=$(curl -s -m 5 https://ifconfig.me 2>/dev/null || curl -s -m 5 https://api.ipify.org)
if [ -z "$EXPECTED_IP" ]; then
    warn "Could not determine this server's public IP"
else
    ok "This server's public IP: ${EXPECTED_IP}"
    ACTUAL_IP=$(getent hosts "$API_DOMAIN" | awk '{print $1}' | head -1)
    if [ -z "$ACTUAL_IP" ]; then
        fail "${API_DOMAIN} does not resolve — add A record in GoDaddy DNS pointing to ${EXPECTED_IP}"
    elif [ "$ACTUAL_IP" = "$EXPECTED_IP" ]; then
        ok "${API_DOMAIN} → ${ACTUAL_IP} (matches this server)"
    else
        fail "${API_DOMAIN} resolves to ${ACTUAL_IP} but this server is ${EXPECTED_IP} — fix DNS"
    fi
fi

# 8. Ports 80 + 443 reachable from outside (best-effort)
if [ -n "${EXPECTED_IP:-}" ]; then
    if curl -s -m 5 -o /dev/null -w "%{http_code}" "http://${EXPECTED_IP}" | grep -qE "^(200|301|302|404|502)$"; then
        ok "Port 80 reachable from outside"
    else
        warn "Port 80 may not be reachable — confirm OCI Security List has TCP 80 ingress from 0.0.0.0/0"
    fi
fi

echo ""
if [ "$ERRORS" -gt 0 ]; then
    echo "${RED}${ERRORS} error(s) — fix before running oci_setup.sh${NC}"
    exit 1
elif [ "$WARNINGS" -gt 0 ]; then
    echo "${YELLOW}${WARNINGS} warning(s) — review then run: bash /opt/tokenforge/deploy/oci_setup.sh ${API_DOMAIN}${NC}"
    exit 0
else
    echo "${GREEN}✅ All checks passed. Run: bash /opt/tokenforge/deploy/oci_setup.sh ${API_DOMAIN}${NC}"
fi
