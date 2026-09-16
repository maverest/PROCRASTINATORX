"""Chargement du catalogue canonique des pays de Mapix."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from unidecode import unidecode


class CatalogError(ValueError):
    """Le catalogue de pays est invalide."""


@dataclass(frozen=True, slots=True)
class Country:
    id: str
    name: str
    continent: str
    flag: str
    aliases: tuple[str, ...]


REGION_CODES = {
    "africa": "DZ AO BJ BW BF BI CV CM CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY MG MW ML MR MU MA MZ NA NE NG RW ST SN SC SL SO ZA SS SD TZ TG TN UG ZM ZW".split(),
    "europe": "AL AD AT BY BE BA BG HR CZ DK EE FI FR DE GR VA HU IS IE IT LV LI LT LU MT MD MC ME NL MK NO PL PT RO RU SM RS SK SI ES SE CH UA GB".split(),
    "asia": "AF AM AZ BH BD BT BN KH CN CY GE IN ID IR IQ IL JP JO KZ KW KG LA LB MY MV MN MM NP KP OM PK PS PH QA SA SG KR LK SY TJ TH TL TR TM AE UZ VN YE".split(),
    "north-america": "AG BS BB BZ CA CR CU DM DO SV GD GT HT HN JM MX NI PA KN LC VC TT US".split(),
    "south-america": "AR BO BR CL CO EC GY PY PE SR UY VE".split(),
    "oceania": "AU FJ KI MH FM NR NZ PW PG WS SB TO TV VU".split(),
}
VALID_COUNTRY_IDS = frozenset(
    country_id for codes in REGION_CODES.values() for country_id in codes
)


def normalize_name(value: str) -> str:
    """Retourne la forme comparable d'un nom de pays ou d'un alias."""
    ascii_value = unidecode(value).lower().replace("’", "'")
    return " ".join(re.sub(r"[^a-z]+", " ", ascii_value).split())


def require_text(row: dict[str, object], key: str) -> str:
    """Exige un texte non vide dans une ligne de catalogue."""
    value = row[key]
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"invalid {key}")
    return value


class CountryCatalog:
    """Index immuables du catalogue validé."""

    VALID_CONTINENTS = (
        "africa", "europe", "asia", "north-america", "south-america", "oceania"
    )

    def __init__(self, countries: tuple[Country, ...]) -> None:
        by_id: dict[str, Country] = {}
        by_normalized_name: dict[str, Country] = {}

        for country in countries:
            if country.id in by_id:
                raise CatalogError(f"duplicate country id: {country.id}")
            by_id[country.id] = country

            self._add_name(by_normalized_name, country.name, country, "name")
            for alias in country.aliases:
                self._add_name(by_normalized_name, alias, country, "alias")

        for country_id in by_id:
            if country_id not in VALID_COUNTRY_IDS:
                raise CatalogError(f"invalid country id: {country_id}")

        self.countries = countries
        self.by_id = by_id
        self.by_normalized_name = by_normalized_name

    @staticmethod
    def _add_name(
        index: dict[str, Country], value: str, country: Country, kind: str
    ) -> None:
        normalized = normalize_name(value)
        existing = index.get(normalized)
        if existing is not None and existing.id != country.id:
            raise CatalogError(f"duplicate {kind}: {value}")
        index[normalized] = country

    @classmethod
    def from_json(cls, path: Path) -> "CountryCatalog":
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise CatalogError("invalid country catalogue")

        countries = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "id", "name", "continent", "flag", "aliases"
            }:
                raise CatalogError("invalid country fields")
            country_id = require_text(row, "id").upper()
            name = require_text(row, "name")
            continent = require_text(row, "continent")
            flag = require_text(row, "flag")
            aliases = row["aliases"]
            if not isinstance(aliases, list) or not all(
                isinstance(item, str) and item.strip() for item in aliases
            ):
                raise CatalogError(f"invalid aliases: {country_id}")
            if continent not in cls.VALID_CONTINENTS:
                raise CatalogError(f"invalid continent: {country_id}")
            countries.append(Country(country_id, name, continent, flag, tuple(aliases)))

        catalog = cls(tuple(countries))
        missing = VALID_COUNTRY_IDS - set(catalog.by_id)
        extra = set(catalog.by_id) - VALID_COUNTRY_IDS
        if missing or extra:
            raise CatalogError(
                "catalogue incomplet: exactement 195 pays attendus "
                f"(absents: {', '.join(sorted(missing)) or '-'}; "
                f"inconnus: {', '.join(sorted(extra)) or '-'})"
            )
        return catalog

    def for_region(self, region: str) -> tuple[Country, ...]:
        """Retourne les pays d'une région de jeu."""
        if region == "world":
            return self.countries
        if region not in self.VALID_CONTINENTS:
            raise CatalogError(f"unknown region: {region}")
        return tuple(country for country in self.countries if country.continent == region)
