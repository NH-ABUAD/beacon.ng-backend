import secrets
import string


def generate_tracking_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f'BCR-{suffix}'
