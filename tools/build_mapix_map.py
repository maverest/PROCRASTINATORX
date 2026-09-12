#!/usr/bin/env python3
"""Convertit un GeoJSON Natural Earth local en carte SVG autonome pour Mapix."""

# Source consultée le 2026-09-12 :
# https://raw.githubusercontent.com/datasets/geo-countries/main/data/countries.geojson
# SHA-256 : 45f41865adec4f86602c2cd05c0e29cd8b437614bf2f5b5a863d12463202cae4
# La source contient France/Norway avec ISO2=-99. Seules ces deux métadonnées
# sont corrigées, après contrôle de couverture et d'unicité ; aucun territoire
# ni aucune géométrie n'est réattribué. Le GeoJSON brut n'est pas embarqué.

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re


TOLERANCE = 0.35
ISO_REPAIRS = {"France": "FR", "Norway": "NO"}


def country_features(source, country_ids):
    features = source["features"]
    present = {f["properties"].get("ISO3166-1-Alpha-2") for f in features}
    missing = country_ids - present
    repairs = {}
    if missing:
        if missing != set(ISO_REPAIRS.values()):
            raise ValueError(f"Codes absents du GeoJSON : {', '.join(sorted(missing))}")
        for name, code in ISO_REPAIRS.items():
            matches = [f for f in features if f["properties"].get("name") == name]
            if len(matches) != 1 or matches[0]["properties"].get("ISO3166-1-Alpha-2") != "-99":
                raise ValueError(f"Correction FR/NO ambiguë ou impossible : {name}")
            repairs[name] = code
    grouped = {code: [] for code in country_ids}
    for feature in features:
        props = feature["properties"]
        code = props.get("ISO3166-1-Alpha-2")
        if code == "-99":
            code = repairs.get(props.get("name"))
        if code not in country_ids:
            continue
        geometry = feature.get("geometry") or {}
        kind = geometry.get("type")
        if kind not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"Géométrie non polygonale pour {code} : {kind}")
        polygons = geometry["coordinates"] if kind == "MultiPolygon" else [geometry["coordinates"]]
        grouped[code].extend(polygons)
    return grouped


def segment_distance_squared(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = dx * dx + dy * dy
    t = max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length)) if length else 0
    return (point[0] - start[0] - t * dx) ** 2 + (point[1] - start[1] - t * dy) ** 2


def rdp(points):
    """RDP itératif pour éviter une profondeur de récursion liée au littoral."""
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        start, end = pending.pop()
        if end - start < 2:
            continue
        index = max(range(start + 1, end), key=lambda i: segment_distance_squared(points[i], points[start], points[end]))
        if segment_distance_squared(points[index], points[start], points[end]) > TOLERANCE ** 2:
            keep.add(index)
            pending.extend(((start, index), (index, end)))
    return [points[i] for i in sorted(keep)]


def ring_path(points):
    # Une boucle fermée est coupée en deux arcs pour ne pas dégénérer en segment.
    split = max(range(1, len(points)), key=lambda i: (points[i][0] - points[0][0]) ** 2 + (points[i][1] - points[0][1]) ** 2)
    simplified = rdp(points[:split + 1])[:-1] + rdp(points[split:] + points[:1])[:-1]
    rounded = [(round(x, 1), round(y, 1)) for x, y in simplified]
    if len(set(rounded)) < 3:
        rounded = [(round(x, 1), round(y, 1)) for x, y in points]
    if len(set(rounded)) < 3:
        # Un îlot inférieur à la précision SVG ne peut former une surface.
        # Son pays conserve une cible si sa géométrie entière est minuscule.
        return ""
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in rounded) + " Z"


def project_ring(ring, code):
    points = []
    for lon, lat, *_ in ring:
        if not math.isfinite(lon) or not math.isfinite(lat) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(f"Coordonnées invalides pour {code}")
        point = ((lon + 180) * 10, (90 - lat) * 10)
        if not points or points[-1] != point:
            points.append(point)
    if len(points) > 1 and points[-1] == points[0]:
        points.pop()
    if len(set(points)) < 3:
        raise ValueError(f"Anneau dégénéré pour {code}")
    return points


def area(ring):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))) / 2


def build_svg(source, catalog):
    country_ids = {row["id"] for row in catalog}
    if not country_ids or any(not re.fullmatch(r"[A-Z]{2}", code) for code in country_ids):
        raise ValueError("Le catalogue doit contenir des codes ISO-2")
    grouped = country_features(source, country_ids)
    paths, targets = [], []
    for code in sorted(grouped):
        polygons = [[project_ring(ring, code) for ring in polygon] for polygon in grouped[code]]
        if not polygons or any(not polygon for polygon in polygons):
            raise ValueError(f"Aucune géométrie pour {code}")
        largest = max(polygons, key=lambda polygon: area(polygon[0]) - sum(area(r) for r in polygon[1:]))
        xs, ys = zip(*largest[0])
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        small = max_x - min_x < 14 or max_y - min_y < 14
        if small:
            targets.append(f'    <circle data-target-country="{code}" cx="{(min_x + max_x) / 2:.1f}" cy="{(min_y + max_y) / 2:.1f}" r="7.0" fill="transparent" pointer-events="all" />')
        parts = []
        for polygon in polygons:
            outer = ring_path(polygon[0])
            if outer:
                parts.append(" ".join(filter(None, [outer] + [ring_path(ring) for ring in polygon[1:]])))
        data = " ".join(sorted(parts))
        if data:
            paths.append(f'    <path data-country="{code}" fill-rule="evenodd" d="{data}" />')
        elif not small:
            raise ValueError(f"Aucune surface ni cible pour {code}")
    return '\n'.join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3600 1800" role="img" aria-label="Carte des pays du monde">',
        '  <g id="mapix-countries">', *paths, '  </g>',
        '  <g id="mapix-targets">', *targets, '  </g>', '</svg>', '',
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        svg = build_svg(json.loads(args.source.read_text(encoding="utf-8")),
                        json.loads(args.catalog.read_text(encoding="utf-8")))
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Erreur de génération : {error}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
