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
    private_pem = v.private_pem().decode()
    public_b64  = v.public_key.public_bytes_raw_format() if hasattr(v.public_key, 'public_bytes_raw_format') else None
    # py_vapid >=1.9 exposes public/private in PEM + base64url uncompressed
    try:
        from py_vapid.utils import b64urlencode
        from cryptography.hazmat.primitives import serialization
        raw = v.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        public_b64 = b64urlencode(raw).decode() if isinstance(b64urlencode(raw), bytes) else b64urlencode(raw)
    except Exception:
        pass

    print('# Add these to your environment (cPanel → Setup Python App → Env Vars):')
    print('VAPID_PUBLIC_KEY=' + (public_b64 or ''))
    print('VAPID_PRIVATE_KEY="' + private_pem.replace('\n', '\\n') + '"')
    print('VAPID_SUBJECT=mailto:admin@mof-eng.com')


if __name__ == '__main__':
    main()
