#!/usr/bin/env bash
# Generates an Android production keystore for Google Play Store submission (Milestone 5.2)
set -e

KEYSTORE_FILE="gofatho-release-key.jks"
ALIAS="gofatho_ai_key"

echo "=== Generating Gofatho AI Android Release Keystore ==="
keytool -genkey -v \
  -keystore "$KEYSTORE_FILE" \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias "$ALIAS" \
  -dname "CN=Gofatho AI Project, OU=Sawula NLP, O=Gofa Zone Community, L=Sawula, ST=South Ethiopia, C=ET"

echo ""
echo "=== GitHub Actions Secret (GOFATHO_KEYSTORE_BASE64) ==="
base64 -w 0 "$KEYSTORE_FILE"
echo ""
echo "Done! Add GOFATHO_KEYSTORE_BASE64, GOFATHO_KEY_ALIAS ($ALIAS), GOFATHO_KEY_PASSWORD, and GOFATHO_STORE_PASSWORD to your GitHub repo Secrets."
