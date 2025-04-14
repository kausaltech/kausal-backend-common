from __future__ import annotations

from kausal_common.context import get_project_id

WILDCARD_DOMAINS_HEADER = 'x-wildcard-domains'
FORWARDED_HEADER = 'forwarded'
FORWARDED_FOR_HEADER = 'x-forwarded-for'

IS_PATHS = get_project_id() == 'paths-backend'
IS_WATCH = get_project_id() == 'watch-backend'
