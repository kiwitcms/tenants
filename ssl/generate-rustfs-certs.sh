#!/bin/bash
#
# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# Generate a throwaway CA and server certificate for the local RustFS
# instance. The certificate is valid for localhost.

set -euo pipefail

DIR="$(dirname "$0")/rustfs"
mkdir -p "$DIR"

/usr/bin/sscg --verbose --force \
    --country BG --locality Sofia \
    --organization "Kiwi TCMS" \
    --organizational-unit "Quality Engineering" \
    --hostname localhost \
    --ca-file       "$DIR/ca.crt" \
    --ca-key-file   "$DIR/ca.key" \
    --ca-key-mode=0600 \
    --cert-file     "$DIR/rustfs_cert.pem" \
    --cert-mode=0644 \
    --cert-key-file "$DIR/rustfs_key.pem" \
    --cert-key-mode=0644

# sscg 3.0.2 emits CA basicConstraints as non-critical, which Python's
# strict X.509 verification rejects. Re-sign the CA certificate with the
# same key/subject and mark the extension critical.
SUBJECT=$(openssl x509 -in "$DIR/ca.crt" -noout -subject -nameopt compat | sed 's/^subject=//')
openssl req -x509 -new -sha256 -days 1 \
    -key "$DIR/ca.key" \
    -subj "$SUBJECT" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -out "$DIR/ca.crt"
