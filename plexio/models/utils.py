import base64

LANGUAGE_TO_EMOJI = {
    'ps': '🇵🇰',
    'uz': '🇺🇿',
    'tk': '🇹🇲',
    'sq': '🇦🇱',
    'ar': '🇦🇪',
    'en': '🇬🇧',
    'sm': '🇼🇸',
    'ca': '🏴󠁥󠁳󠁣󠁴󠁿',
    'pt': '🇵🇹',
    'es': '🇪🇸',
    'gn': '🇵🇾',
    'hy': '🇦🇲',
    'ru': '🇷🇺',
    'nl': '🇳🇱',
    'pa': '🇮🇳',
    'de': '🇩🇪',
    'az': '🇦🇿',
    'bn': '🇧🇩',
    'be': '🇧🇾',
    'fr': '🇫🇷',
    'dz': '🇧🇹',
    'ay': '🇧🇴',
    'qu': '🇧🇴',
    'bs': '🇧🇦',
    'hr': '🇭🇷',
    'sr': '🇷🇸',
    'tn': '🇹🇳',
    'no': '🇧🇻',
    'nb': '🇧🇻',
    'nn': '🇧🇻',
    'ms': '🇲🇾',
    'bg': '🇧🇬',
    'ff': '🇸🇳',
    'rn': '🇧🇮',
    'km': '🇰🇭',
    'sg': '🇨🇫',
    'zh': '🇨🇳',
    'ln': '🇨🇩',
    'kg': '🇨🇬',
    'sw': '🇹🇿',
    'lu': '🇨🇩',
    'el': '🇬🇷',
    'tr': '🇹🇷',
    'cs': '🇨🇿',
    'sk': '🇸🇰',
    'da': '🇩🇰',
    'ti': '🇪🇷',
    'et': '🇪🇪',
    'ss': '🇸🇿',
    'am': '🇪🇹',
    'fo': '🇫🇴',
    'fj': '🇫🇯',
    'hi': '🇮🇳',
    'ur': '🇵🇰',
    'fi': '🇫🇮',
    'sv': '🇸🇪',
    'ka': '🇬🇪',
    'kl': '🇬🇱',
    'ch': '🇬🇺',
    'ht': '🇭🇹',
    'it': '🇮🇹',
    'la': '🇻🇦',
    'hu': '🇭🇺',
    'is': '🇮🇸',
    'id': '🇮🇩',
    'fa': '🇮🇷',
    'ku': '🇮🇶',
    'ga': '🇮🇪',
    'gv': '🇮🇲',
    'he': '🇮🇱',
    'ja': '🇯🇵',
    'kk': '🇰🇿',
    'ko': '🇰🇷',
    'ky': '🇰🇬',
    'lo': '🇱🇦',
    'lv': '🇱🇻',
    'st': '🇱🇸',
    'lt': '🇱🇹',
    'lb': '🇱🇺',
    'mg': '🇲🇬',
    'ny': '🇲🇼',
    'dv': '🇲🇻',
    'mt': '🇲🇹',
    'mh': '🇲🇭',
    'ro': '🇲🇩',
    'mn': '🇲🇳',
    'my': '🇲🇲',
    'af': '🇳🇦',
    'na': '🇳🇷',
    'ne': '🇳🇵',
    'mi': '🇳🇿',
    'mk': '🇲🇰',
    'pl': '🇵🇱',
    'rw': '🇷🇼',
    'ta': '🇮🇳',
    'sl': '🇸🇮',
    'so': '🇸🇴',
    'nr': '🇿🇦',
    'ts': '🇿🇦',
    've': '🇿🇦',
    'xh': '🇿🇦',
    'zu': '🇿🇦',
    'eu': '🇪🇸',
    'gl': '🇪🇸',
    'oc': '🇪🇸',
    'si': '🇱🇰',
    'tg': '🇹🇯',
    'th': '🇹🇭',
    'to': '🇹🇴',
    'uk': '🇺🇦',
    'bi': '🇻🇺',
    'vi': '🇻🇳',
    'sn': '🇿🇼',
    'nd': '🇿🇦',
}

PLEXIO_PREFIX = 'plexio:'


def get_flag_emoji(code):
    return LANGUAGE_TO_EMOJI.get(code, code)


def to_camel(string: str) -> str:
    words = string.split('_')
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])


def guid_to_plexio_id(guid: str, server_index: int | None = None) -> str:
    encoded_guid = base64.urlsafe_b64encode(guid.encode()).rstrip(b'=').decode()
    if server_index is not None:
        return f'{PLEXIO_PREFIX}{server_index}:{encoded_guid}'
    return PLEXIO_PREFIX + encoded_guid


def parse_plexio_id(plexio_id: str) -> tuple[int | None, str]:
    """Parse a plexio ID into (server_index, guid).

    Supports both legacy format ``plexio:<b64>`` and new marked format
    ``plexio:<index>:<b64>``.  For legacy IDs the server_index is ``None``.
    """
    without_prefix = plexio_id[len(PLEXIO_PREFIX) :]
    parts = without_prefix.split(':', maxsplit=1)
    if len(parts) == 2 and parts[0].isdigit():
        server_index = int(parts[0])
        encoded_guid = parts[1]
    else:
        server_index = None
        encoded_guid = without_prefix
    padding = 4 - (len(encoded_guid) % 4)
    encoded_guid += '=' * padding
    return server_index, base64.urlsafe_b64decode(encoded_guid).decode()


def plexio_id_to_guid(plexio_id: str) -> str:
    _, guid = parse_plexio_id(plexio_id)
    return guid
