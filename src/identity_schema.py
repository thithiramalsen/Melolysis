"""Versioned catalog contracts; identifiers never depend on display names."""
from uuid import UUID, uuid5

NAMESPACE = UUID('0564175d-0822-4c09-982c-f4a2af83e202')
FORMAT = 'melolysis-catalog-v1'


def recording_id(source):
    return uuid5(NAMESPACE, 'recording:' + source).hex


def label(value, field, required=False):
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError(f'{field} must be text of at most 200 characters')
    value = value.strip()
    if required and not value:
        raise ValueError(f'Enter {field}')
    return value
