from django.core.exceptions import ValidationError

MAX_DESCRIPTION_LENGTH = 5000
MIN_DESCRIPTION_LENGTH = 20
MAX_EVIDENCE_FILE_SIZE = 20 * 1024 * 1024
MAX_EVIDENCE_COUNT = 10
ALLOWED_IMAGE_TYPES = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_VIDEO_TYPES = {'mp4', 'mov', 'avi'}
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'video/mp4',
    'video/quicktime',
    'video/x-msvideo',
}


def validate_description(value):
    if not isinstance(value, str):
        raise ValidationError('Description must be a string.')
    value = value.strip()
    if not (MIN_DESCRIPTION_LENGTH <= len(value) <= MAX_DESCRIPTION_LENGTH):
        raise ValidationError(
            f'Description must be between {MIN_DESCRIPTION_LENGTH} and {MAX_DESCRIPTION_LENGTH} characters.'
        )
    return value


def validate_coordinate(field_name, value):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f'{field_name} must be a valid number.')

    if field_name == 'latitude' and not -90 <= numeric_value <= 90:
        raise ValidationError('Latitude must be between -90 and 90.')
    if field_name == 'longitude' and not -180 <= numeric_value <= 180:
        raise ValidationError('Longitude must be between -180 and 180.')

    return numeric_value


def validate_evidence_file(file_obj):
    if file_obj.size > MAX_EVIDENCE_FILE_SIZE:
        raise ValidationError(f'File size cannot exceed {MAX_EVIDENCE_FILE_SIZE // (1024 * 1024)}MB.')

    extension = file_obj.name.split('.')[-1].lower()
    mime_type = file_obj.content_type or ''
    if extension in ALLOWED_IMAGE_TYPES and mime_type.startswith('image/'):
        return
    if extension in ALLOWED_VIDEO_TYPES and mime_type.startswith('video/'):
        return
    if mime_type in ALLOWED_MIME_TYPES:
        return
    raise ValidationError('Unsupported file type. Use JPG, JPEG, PNG, WEBP, MP4, MOV, or AVI files.')


def validate_evidence_file_count(report):
    if report.evidence.count() >= MAX_EVIDENCE_COUNT:
        raise ValidationError(f'You cannot upload more than {MAX_EVIDENCE_COUNT} files per report.')
