import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


private_key = ec.generate_private_key(ec.SECP256R1())
private_value = private_key.private_numbers().private_value.to_bytes(32, "big")
public_numbers = private_key.public_key().public_numbers()
public_value = b"\x04" + public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")

print(f"WEB_PUSH_VAPID_PUBLIC_KEY={_b64url(public_value)}")
print(f"WEB_PUSH_VAPID_PRIVATE_KEY={_b64url(private_value)}")
