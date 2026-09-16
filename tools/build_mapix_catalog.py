#!/usr/bin/env python3
"""Génère le catalogue Mapix à partir des territoires français de Babel."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

from babel import Locale
from unidecode import unidecode


REGION_CODES = {
    "africa": "DZ AO BJ BW BF BI CV CM CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY MG MW ML MR MU MA MZ NA NE NG RW ST SN SC SL SO ZA SS SD TZ TG TN UG ZM ZW".split(),
    "europe": "AL AD AT BY BE BA BG HR CZ DK EE FI FR DE GR VA HU IS IE IT LV LI LT LU MT MD MC ME NL MK NO PL PT RO RU SM RS SK SI ES SE CH UA GB".split(),
    "asia": "AF AM AZ BH BD BT BN KH CN CY GE IN ID IR IQ IL JP JO KZ KW KG LA LB MY MV MN MM NP KP OM PK PS PH QA SA SG KR LK SY TJ TH TL TR TM AE UZ VN YE".split(),
    "north-america": "AG BS BB BZ CA CR CU DM DO SV GD GT HT HN JM MX NI PA KN LC VC TT US".split(),
    "south-america": "AR BO BR CL CO EC GY PY PE SR UY VE".split(),
    "oceania": "AU FJ KI MH FM NR NZ PW PG WS SB TO TV VU".split(),
}

ALIASES = {
    "AE": ["Émirats arabes unis", "EAU"],
    "BA": ["Bosnie", "Bosnie Herzégovine"],
    "CD": ["RDC", "Congo Kinshasa", "Congo-Kinshasa"],
    "CG": ["Congo Brazzaville", "Congo-Brazzaville"],
    "CI": ["Cote d Ivoire"],
    "CZ": ["République tchèque"],
    "GB": ["Royaume Uni", "Grande Bretagne", "UK"],
    "KP": ["Corée du Nord"],
    "KR": ["Corée du Sud"],
    "LA": ["Laos"],
    "MD": ["Moldavie"],
    "MK": ["Macédoine", "Macédoine du Nord"],
    "MM": ["Myanmar", "Birmanie"],
    "PS": ["Palestine"],
    "RU": ["Russie"],
    "SZ": ["Swaziland"],
    "TR": ["Turquie"],
    "TZ": ["Tanzanie"],
    "US": ["États-Unis", "Etats Unis", "USA"],
    "VA": ["Vatican", "Saint-Siège"],
    "VN": ["Vietnam", "Viet Nam"],
}


def flag_for(code: str) -> str:
    return "".join(chr(0x1F1E6 + ord(letter) - ord("A")) for letter in code)


def normalize_name(value: str) -> str:
    ascii_value = unidecode(value).lower().replace("’", "'")
    return " ".join(re.sub(r"[^a-z]+", " ", ascii_value).split())


def build_catalog() -> list[dict[str, object]]:
    """Construit les lignes, dans l'ordre canonique de leurs continents."""
    locale = Locale("fr")
    countries = []
    for continent, codes in REGION_CODES.items():
        rows = [
            {
                "id": code,
                "name": locale.territories[code],
                "continent": continent,
                "flag": flag_for(code),
                "aliases": ALIASES.get(code, []),
            }
            for code in codes
        ]
        countries.extend(sorted(rows, key=lambda row: normalize_name(str(row["name"]))))
    return countries


def main(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_catalog(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} OUTPUT_PATH")
    main(Path(sys.argv[1]))
