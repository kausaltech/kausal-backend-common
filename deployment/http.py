from __future__ import annotations

import re
import string
from dataclasses import dataclass
from re import Pattern
from typing import Final

from kausal_common.const import WILDCARD_DOMAINS_HEADER


def get_allowed_cors_headers() -> list[str]:
    return [
        WILDCARD_DOMAINS_HEADER,
        'sentry-trace',
        'baggage',
        'tracecontext',
        'tracestate',
        'referer',
        'forwarded',
        'x-forwarded-for',
    ]


@dataclass
class ForwardedHeader:
    host: str | None = None
    proto: str | None = None
    for_: str | None = None
    by: str | None = None


_TCHAR: Final[str] = string.digits + string.ascii_letters + r"!#$%&'*+.^_`|~-"
# '-' at the end to prevent interpretation as range in a char class

_TOKEN: Final[str] = rf"[{_TCHAR}]+"

_QDTEXT: Final[str] = r"[{}]".format(
    r"".join(chr(c) for c in (0x09, 0x20, 0x21) + tuple(range(0x23, 0x7F)))
)
# qdtext includes 0x5C to escape 0x5D ('\]')
# qdtext excludes obs-text (because obsoleted, and encoding not specified)

_QUOTED_PAIR: Final[str] = r"\\[\t !-~]"

_QUOTED_STRING: Final[str] = r'"(?:{quoted_pair}|{qdtext})*"'.format(  # noqa: UP032
    qdtext=_QDTEXT, quoted_pair=_QUOTED_PAIR
)

_FORWARDED_PAIR: Final[str] = (
    r"({token})=({token}|{quoted_string})(:\d{{1,4}})?".format(  # noqa: UP032
        token=_TOKEN, quoted_string=_QUOTED_STRING
    )
)

_QUOTED_PAIR_REPLACE_RE: Final[Pattern[str]] = re.compile(r"\\([\t !-~])")
# same pattern as _QUOTED_PAIR but contains a capture group

_FORWARDED_PAIR_RE: Final[Pattern[str]] = re.compile(_FORWARDED_PAIR)

# lifted from https://github.com/aio-libs/aiohttp/blob/master/aiohttp/web_request.py
def _parse_forwarded(values: list[str]) -> list[dict[str, str]]:
    """
    A tuple containing all parsed Forwarded header(s).

    Makes an effort to parse Forwarded headers as specified by RFC 7239:

    - It adds one (immutable) dictionary per Forwarded 'field-value', ie
        per proxy. The element corresponds to the data in the Forwarded
        field-value added by the first proxy encountered by the client. Each
        subsequent item corresponds to those added by later proxies.
    - It checks that every value has valid syntax in general as specified
        in section 4: either a 'token' or a 'quoted-string'.
    - It un-escapes found escape sequences.
    - It does NOT validate 'by' and 'for' contents as specified in section
        6.
    - It does NOT validate 'host' contents (Host ABNF).
    - It does NOT validate 'proto' contents for valid URI scheme names.

    Returns a tuple containing one or more immutable dicts
    """  # noqa: D401
    elems: list[dict[str, str]] = []
    for field_value in values:
        length = len(field_value)
        pos = 0
        need_separator = False
        elem: dict[str, str] = {}
        elems.append(elem)
        while 0 <= pos < length:
            match = _FORWARDED_PAIR_RE.match(field_value, pos)
            if match is not None:  # got a valid forwarded-pair
                if need_separator:
                    # bad syntax here, skip to next comma
                    pos = field_value.find(",", pos)
                else:
                    name, value, port = match.groups()
                    if value[0] == '"':
                        # quoted string: remove quotes and unescape
                        value = _QUOTED_PAIR_REPLACE_RE.sub(r"\1", value[1:-1])
                    if port:
                        value += port
                    elem[name.lower()] = value
                    pos += len(match.group(0))
                    need_separator = True
            elif field_value[pos] == ",":  # next forwarded-element
                need_separator = False
                elem = {}
                elems.append(elem)
                pos += 1
            elif field_value[pos] == ";":  # next forwarded-pair
                need_separator = False
                pos += 1
            elif field_value[pos] in " \t":
                # Allow whitespace even between forwarded-pairs, though
                # RFC 7239 doesn't. This simplifies code and is in line
                # with Postel's law.
                pos += 1
            else:
                # bad syntax here, skip to next comma
                pos = field_value.find(",", pos)
    return elems


def parse_forwarded(values: list[str]) -> list[ForwardedHeader]:
    """Parse the Forwarded HTTP header."""

    parsed = _parse_forwarded(values)
    headers = []
    for data in parsed:
        header = ForwardedHeader(
            host=data.get('host'),
            proto=data.get('proto'),
            for_=data.get('for'),
            by=data.get('by'),
        )
        headers.append(header)

    return headers
