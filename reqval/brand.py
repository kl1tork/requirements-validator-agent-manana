"""Фирменный знак Manana: зелёный щит с золотой кромкой и белой буквой M."""
from __future__ import annotations

import base64

LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="Manana">'
    '<path d="M60 8l44 16v30c0 28-19 48-44 58C35 102 16 82 16 54V24z" fill="#0a6b45"/>'
    '<path d="M60 8l44 16v30c0 28-19 48-44 58" fill="none" stroke="#c9a227" stroke-width="5"/>'
    '<path d="M38 78V44l22 20 22-20v34" fill="none" stroke="#fff" stroke-width="9" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)

FAVICON = "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.encode()).decode()


def logo(size: int = 40) -> str:
    """Логотип для вставки в HTML нужного размера."""
    return LOGO_SVG.replace("<svg ", f'<svg width="{size}" height="{size}" class="logo-svg" ', 1)
