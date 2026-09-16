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
REGION_VIEWS = {
    "world": (0, 0, 3600, 1800),
    "africa": (1350, 500, 1050, 1150),
    "europe": (1550, 250, 950, 650),
    "asia": (1900, 180, 1600, 1050),
    "north-america": (0, 220, 1500, 1000),
    "south-america": (850, 780, 950, 1000),
    # Le cadrage traverse l'antiméridien. map.js y duplique uniquement les
    # formes proches du bord gauche, translatées d'une largeur de monde.
    "oceania": (2650, 700, 1350, 800),
}
WRAP_X = 3600
WRAP_THRESHOLD = 400

# Relief volontairement stylisé et léger : ces tracés décoratifs utilisent la
# même projection équirectangulaire que les pays et restent sous les zones de
# jeu, afin que les états trouvé/erreur gardent toujours la priorité visuelle.
PHYSICAL_LAYERS = [
    '  <g id="mapix-relief" pointer-events="none">',
    '    <path d="M640,400 L700,470 L735,545 L760,625 L790,700" />',  # Rocheuses
    '    <path d="M1045,830 L1090,960 L1115,1090 L1145,1230 L1180,1390 L1220,1510" />',  # Andes
    '    <path d="M1690,585 L1780,565 L1870,575 L1940,565" />',  # Atlas
    '    <path d="M1880,440 L1940,425 L2010,440 L2070,425" />',  # Alpes / Carpates
    '    <path d="M2450,590 L2540,565 L2640,575 L2740,550 L2830,570" />',  # Himalaya
    '    <path d="M2140,835 L2160,910 L2180,1010" />',  # hauts plateaux d\'Afrique orientale
    '    <path d="M3180,1110 L3230,1190 L3270,1300 L3300,1400" />',  # cordillère australienne
    '    <path d="M940,500 L990,550 L1040,610" />',  # Appalaches
    '  </g>',
    '  <g id="mapix-lakes" pointer-events="none">',
    '    <path d="M920,450 L965,435 L1005,455 L990,480 L945,482 Z" />',  # Grands Lacs
    '    <path d="M2285,515 L2325,485 L2350,535 L2330,590 L2295,570 Z" />',  # Caspienne
    '    <path d="M2115,900 L2150,895 L2165,920 L2130,930 Z" />',  # Victoria
    '    <path d="M2085,955 L2100,950 L2110,1025 L2095,1040 Z" />',  # Tanganyika
    '    <path d="M2840,420 L2885,390 L2940,405 L2910,430 L2860,435 Z" />',  # Baïkal
    '    <path d="M1100,1050 L1120,1045 L1130,1070 L1110,1080 Z" />',  # Titicaca
    '    <path d="M2385,440 L2415,435 L2425,460 L2395,465 Z" />',  # Aral
    '  </g>',
]


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
    view_attributes = " ".join(
        f'data-view-{region}="{" ".join(map(str, view))}"'
        for region, view in REGION_VIEWS.items()
    )
    return '\n'.join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3600 1800" '
        'role="img" aria-label="Carte des pays du monde" '
        f'data-wrap-x="{WRAP_X}" data-wrap-threshold="{WRAP_THRESHOLD}" '
        f'{view_attributes}>',
        *PHYSICAL_LAYERS,
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
