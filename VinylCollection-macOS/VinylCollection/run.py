"""Vinyl Collection Dashboard — launcher."""
from __future__ import annotations

import json
import sys
import os
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _here


_SETTINGS_FILE = _app_root() / "settings.json"


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        return json.loads(_SETTINGS_FILE.read_text())
    return {}


def _save_settings(settings: dict):
    _SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


def _get_db_path() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            sys.argv.pop(i)
            sys.argv.pop(i)
            settings = _load_settings()
            settings["db_path"] = db_path
            _save_settings(settings)
            return db_path
    settings = _load_settings()
    return settings.get("db_path", str(_app_root() / "vinyl.db"))


def _get_ssl_args() -> tuple[str, str]:
    """Extract --ssl-cert and --ssl-key arguments."""
    cert = ""
    key = ""
    for i, arg in enumerate(sys.argv):
        if arg == "--ssl-cert" and i + 1 < len(sys.argv):
            cert = sys.argv[i + 1]
            sys.argv.pop(i)
            sys.argv.pop(i)
            break
    for i, arg in enumerate(sys.argv):
        if arg == "--ssl-key" and i + 1 < len(sys.argv):
            key = sys.argv[i + 1]
            sys.argv.pop(i)
            sys.argv.pop(i)
            break
    return cert, key


def _generate_self_signed_cert() -> tuple[str, str]:
    """Generate self-signed SSL certificate if it doesn't exist."""
    cert_path = _app_root() / "cert.pem"
    key_path = _app_root() / "key.pem"
    
    if cert_path.exists() and key_path.exists():
        return str(cert_path), str(key_path)
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        print("Generating self-signed SSL certificate...")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Write key to file
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Write cert to file
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        print(f"✓ SSL certificate generated at {cert_path}")
        return str(cert_path), str(key_path)
    except Exception as e:
        print(f"⚠ Failed to generate SSL certificate: {e}")
        print("  Install cryptography package: pip install cryptography")
        return "", ""


def main():
    db_path = _get_db_path()
    ssl_cert, ssl_key = _get_ssl_args()
    
    # Auto-generate self-signed cert for HTTPS if not provided
    if not ssl_cert or not ssl_key:
        ssl_cert, ssl_key = _generate_self_signed_cert()
    
    import webapp
    webapp.main(db_path=db_path, ssl_cert=ssl_cert, ssl_key=ssl_key)


if __name__ == "__main__":
    main()
