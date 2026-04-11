#!/usr/bin/env python3
"""
Quick test to verify SSL certificate generation works.
Usage: python test_ssl_setup.py
"""

from pathlib import Path
import sys

# Add app folder to path
_app_root = Path(__file__).resolve().parent / "VinylCollection-macOS" / "VinylCollection"
sys.path.insert(0, str(_app_root))

def test_ssl_generation():
    """Test that SSL certificate can be generated."""
    from run import _generate_self_signed_cert, _app_root as run_app_root
    
    print("Testing SSL certificate generation...")
    print(f"App root: {run_app_root}")
    
    cert_path, key_path = _generate_self_signed_cert()
    
    if cert_path and key_path:
        print(f"✓ Certificate: {cert_path}")
        print(f"✓ Key: {key_path}")
        
        # Verify files exist
        if Path(cert_path).exists() and Path(key_path).exists():
            print("✓ SSL files created successfully")
            
            # Check file sizes
            cert_size = Path(cert_path).stat().st_size
            key_size = Path(key_path).stat().st_size
            print(f"  Certificate size: {cert_size} bytes")
            print(f"  Key size: {key_size} bytes")
            
            return True
        else:
            print("✗ SSL files not found after generation")
            return False
    else:
        print("✗ SSL certificate generation failed")
        print("  Ensure cryptography package is installed: pip install cryptography")
        return False

if __name__ == "__main__":
    try:
        success = test_ssl_generation()
        if success:
            print("\n✓ SSL setup test PASSED")
            sys.exit(0)
        else:
            print("\n✗ SSL setup test FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
