"""Generate VAPID keypair for Web Push.

Run once on the server (or locally), then export the printed env vars
into your hosting environment (cPanel → Setup Python App → Environment
variables) and restart Passenger.

    python scripts/gen_vapid_keys.py
"""
from py_vapid import Vapid01 as Vapid


def main():
    v = Vapid()
    v.generate_keys()

    # Public key: raw uncompressed point, base64url-encoded (single line)
    from py_vapid.utils import b64urlencode
    from cryptography.hazmat.primitives import serialization
    pub_raw = v.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_enc = b64urlencode(pub_raw)
    public_b64 = pub_enc.decode() if isinstance(pub_enc, bytes) else pub_enc

    # Private key: 32-byte scalar, base64url-encoded (single line, NO newlines)
    # This is the format py_vapid accepts via Vapid01.from_raw(...) and
    # webpush() accepts as `vapid_private_key`. Far safer than PEM in env vars.
    priv_int   = v.private_key.private_numbers().private_value
    priv_bytes = priv_int.to_bytes(32, 'big')
    priv_enc   = b64urlencode(priv_bytes)
    private_b64 = priv_enc.decode() if isinstance(priv_enc, bytes) else priv_enc

    print('# Add these in cPanel -> Setup Python App -> Environment variables.')
    print('# Paste the VALUE only (no surrounding quotes, no extra spaces).')
    print('# Then click Save and Restart the Python app.')
    print()
    print('VAPID_PUBLIC_KEY=' + public_b64)
    print('VAPID_PRIVATE_KEY=' + private_b64)
    print('VAPID_SUBJECT=mailto:admin@mof-eng.com')


if __name__ == '__main__':
    main()
