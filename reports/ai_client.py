import requests
from django.conf import settings

AI_API_BASE = getattr(settings, 'AI_API_BASE_URL',
                      'https://crime-ai-api-fjf1.onrender.com/api')


def classify_report(description):
    """
    Calls the AI classification service to get crime_type, severity, and
    recommended_dispatch_unit for a report description. Returns the data
    dict, or None if the call fails for any reason. Never raises — report
    submission must not depend on this service being up.
    """
    try:
        response = requests.post(
            f'{AI_API_BASE}/classify',
            json={'description': description},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get('success'):
            return payload.get('data')
        return None
    except (requests.RequestException, ValueError):
        return None


def sync_report_to_ai(description, latitude, longitude, address):
    """
    Forwards a created report to the AI service. Returns the AI's response
    data (dispatch unit, translation, confidence, etc.) so it can be saved
    locally, or None if the sync fails. Never raises.
    """
    try:
        response = requests.post(
            f'{AI_API_BASE}/reports',
            json={
                'description': description,
                'latitude': float(latitude),
                'longitude': float(longitude),
                'location_text': address,
                'source': 'beacon_app',
            },
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get('success'):
            return payload.get('data')
        return None
    except (requests.RequestException, ValueError):
        return None

def classify_audio(audio_file):
    """
    Sends an audio file to the AI service for transcription and classification.
    Returns (data, None) on success, or (None, error_message) on failure.
    Never raises.
    """
    try:
        response = requests.post(
            f'{AI_API_BASE}/classify-audio',
            files={'audio': (audio_file.name, audio_file.read(), audio_file.content_type)},
            timeout=30,
        )
        if response.status_code == 422:
            return None, "The audio could not be understood. Please try recording again, more clearly."
        if response.status_code == 400:
            return None, "Unsupported audio format or file too large. Please use flac, mp3, mp4, mpeg, m4a, ogg, wav, or webm under 25MB."
        response.raise_for_status()
        payload = response.json()
        if payload.get('success'):
            return payload.get('data'), None
        return None, "Could not process the audio. Please try again."
    except (requests.RequestException, ValueError):
        return None, "Could not reach the transcription service. Please try again or submit a text report."