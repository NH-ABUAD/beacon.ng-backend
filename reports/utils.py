import secrets
import string


def generate_tracking_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f'BCR-{suffix}'


NIGERIAN_STATES = [
    'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue',
    'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu',
    'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi',
    'Kwara', 'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo',
    'Plateau', 'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara',
]

# Common aliases seen in real addresses, mapped to the AI service's expected value
STATE_ALIASES = {
    'FCT': 'FCT',
    'Abuja': 'FCT',
    'Federal Capital Territory': 'FCT',
}


def extract_state_hint(address):
    """
    Best-effort extraction of a Nigerian state name from a free-text address.
    Returns the matched state name, or None if nothing confidently matches.
    """
    if not address:
        return None

    address_lower = address.lower()

    for alias, resolved in STATE_ALIASES.items():
        if alias.lower() in address_lower:
            return resolved

    for state in NIGERIAN_STATES:
        if state.lower() in address_lower:
            return state

    return None
