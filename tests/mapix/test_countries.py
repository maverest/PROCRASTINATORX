from collections import Counter
import json
from pathlib import Path

import pytest

from games.mapix.countries import CatalogError, CountryCatalog, normalize_name

ROOT = Path(__file__).parents[2]
CATALOG_PATH = ROOT / "static/mapix/countries.json"


@pytest.fixture(scope="module")
def catalog():
    return CountryCatalog.from_json(CATALOG_PATH)


def test_catalog_contains_195_unique_countries(catalog):
    assert len(catalog.by_id) == 195
    assert set(catalog.by_id) == {country.id for country in catalog.countries}


def test_continent_totals_are_disjoint(catalog):
    assert Counter(country.continent for country in catalog.countries) == {
        "africa": 54,
        "europe": 44,
        "asia": 48,
        "north-america": 23,
        "south-america": 12,
        "oceania": 14,
    }
    assert len(catalog.for_region("world")) == 195


def test_transcontinental_assignments_follow_spec(catalog):
    expected = {
        "RU": "europe", "TR": "asia", "CY": "asia", "GE": "asia",
        "AM": "asia", "AZ": "asia", "KZ": "asia", "EG": "africa",
    }
    assert {code: catalog.by_id[code].continent for code in expected} == expected


def test_names_and_aliases_are_unique_after_normalization(catalog):
    assert catalog.by_normalized_name["etats unis"].id == "US"
    assert catalog.by_normalized_name["usa"].id == "US"
    assert normalize_name("  Côte-d’Ivoire ") == "cote d ivoire"


@pytest.mark.parametrize("value", ["Myanmar", "myanmar", "Birmanie", "BIRMANIE"])
def test_myanmar_accepts_both_current_and_historical_names(catalog, value):
    assert catalog.by_normalized_name[normalize_name(value)].id == "MM"


def test_production_json_rejects_a_catalog_missing_one_country(tmp_path):
    rows = CATALOG_PATH.read_text(encoding="utf-8")
    countries = json.loads(rows)
    path = tmp_path / "countries.json"
    path.write_text(json.dumps(countries[:-1]), encoding="utf-8")

    with pytest.raises(CatalogError, match="195|complet"):
        CountryCatalog.from_json(path)


def test_invalid_duplicate_alias_is_rejected(tmp_path):
    path = tmp_path / "countries.json"
    path.write_text('[{"id":"AA","name":"Alpha","continent":"europe","flag":"A","aliases":["x"]},{"id":"BB","name":"Beta","continent":"europe","flag":"B","aliases":["x"]}]')
    with pytest.raises(CatalogError, match="alias"):
        CountryCatalog.from_json(path)
