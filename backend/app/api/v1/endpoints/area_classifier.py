"""
Area classification and keyword-based area lookup.
"""

from .layout_constants import (
    AREA_PREFIX_RE,
    DEPT_AREA_KEYWORDS,
    PROJECT_AREA_KEYWORDS,
    IT_AREA_KEYWORDS,
    HO_AREA_KEYWORDS,
    normalize_text,
)


def infer_area_prefix(areas: list) -> str:
    counts: dict[str, int] = {}
    for area in areas:
        match = AREA_PREFIX_RE.match(area.name or "")
        if not match:
            continue
        prefix = f"{match.group(1)}{match.group(2)}"
        counts[prefix] = counts.get(prefix, 0) + 1
    if not counts:
        return ""
    return max(counts.items(), key=lambda item: item[1])[0]


def find_area_by_keywords(areas: list, keywords: list[str]) -> object | None:
    for area in areas:
        label = normalize_text(area.name)
        if any(keyword in label for keyword in keywords):
            return area
    return None


def find_best_access_area(areas: list, device_name: str) -> object | None:
    name = normalize_text(device_name)
    if any(keyword in name for keyword in ["dept", "department"]):
        return find_area_by_keywords(areas, DEPT_AREA_KEYWORDS)
    if any(keyword in name for keyword in ["project", "proj"]):
        return find_area_by_keywords(areas, PROJECT_AREA_KEYWORDS)
    if " it" in f" {name} " or name.endswith("it") or name.startswith("it"):
        return find_area_by_keywords(areas, IT_AREA_KEYWORDS)
    if any(keyword in name for keyword in ["ho", "hq", "head"]):
        return find_area_by_keywords(areas, HO_AREA_KEYWORDS)
    return None
