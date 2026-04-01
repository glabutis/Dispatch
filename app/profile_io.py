"""Pure functions for exporting and importing profiles."""

import uuid
from dataclasses import asdict
from typing import List, Tuple

from .config import Profile, Template, _parse_mappings


def export_profile(profile: Profile, templates: List[Template]) -> dict:
    """Serialize a profile + its referenced templates to a dict."""
    template_ids = {m.template_id for m in profile.mappings if m.template_id}
    used_templates = [t for t in templates if t.id in template_ids]
    return {
        "dispatch_export_version": 1,
        "profile": {
            "id": profile.id,
            "name": profile.name,
            "mappings": [asdict(m) for m in profile.mappings],
        },
        "templates": [asdict(t) for t in used_templates],
    }


def import_profile(data: dict, existing_templates: List[Template]) -> Tuple[Profile, List[Template]]:
    """
    Import a profile from exported data.

    Returns (new_profile, list_of_new_templates).
    Raises ValueError on bad input.
    """
    if data.get("dispatch_export_version") != 1:
        raise ValueError("Unrecognized export version or format.")

    raw_profile = data.get("profile")
    if not raw_profile:
        raise ValueError("Missing 'profile' key in export data.")

    # Import templates, dedup by id
    existing_ids = {t.id for t in existing_templates}
    new_templates = []
    for t in data.get("templates", []):
        if t.get("id") not in existing_ids:
            try:
                sanitized = {k: v for k, v in t.items() if k in Template.__dataclass_fields__}
                if isinstance(sanitized.get("label"), str):
                    sanitized["label"] = sanitized["label"][:256]
                new_templates.append(Template(**sanitized))
            except Exception as e:
                raise ValueError(f"Invalid template data: {e}")

    # Import mappings with migration for new fields
    mappings = _parse_mappings(raw_profile.get("mappings", []))

    # Fresh UUID so it never collides with an existing profile
    profile = Profile(
        id=str(uuid.uuid4()),
        name=str(raw_profile.get("name", "Imported"))[:256],
        mappings=mappings,
    )

    return profile, new_templates
