import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).parents[2]
SVG_NAMESPACE = 'xmlns="http://www.w3.org/2000/svg"'


def test_template_exposes_mapix_panels_and_controls():
    html = (ROOT / "templates/mapix/index.html").read_text()
    for element_id in (
        "setupPanel", "gamePanel", "resultPanel", "fatalPanel",
        "modeChoices", "regionChoices", "playButton", "quitButton",
        "retryButton", "menuButton", "mapContainer", "flagPanel", "flagGrid",
        "countryPrompt", "progressValue", "timerValue", "nameForm", "nameInput",
        "resultTime", "resultPerfect", "resultErrors", "resultAccuracy",
    ):
        assert f'id="{element_id}"' in html
    assert '<script src="/static/mapix/game.js" defer></script>' in html
    assert '<script src="/static/mapix/map.js" defer></script>' in html
    assert html.index('/static/mapix/map.js') < html.index('/static/mapix/game.js')
    assert '<link rel="stylesheet" href="/static/mapix/style.css">' in html
    assert "<script>" not in html
    assert html.index('id="mapContainer"') < html.index('id="flagPanel"')


def test_setup_lists_four_modes_and_seven_regions():
    html = (ROOT / "templates/mapix/index.html").read_text()
    for value in ("territory", "flag-territory", "flag-only", "all"):
        assert f'data-mode="{value}"' in html
    for value in ("world", "africa", "europe", "asia", "north-america", "south-america", "oceania"):
        assert f'data-region="{value}"' in html


def test_map_script_loads_local_svg_and_exposes_controller():
    script = (ROOT / "static/mapix/map.js").read_text()
    assert "fetch('/static/mapix/world.svg')" in script
    assert "window.MapixMap" in script
    for method in ("setRegion", "setFound", "flashWrong", "markCorrect", "destroy"):
        assert method in script
    for interaction in ("wheel", "pointermove", "data-country", "data-target-country"):
        assert interaction in script


def test_template_provides_accessible_setup_and_feedback():
    html = (ROOT / "templates/mapix/index.html").read_text()
    assert html.count('aria-pressed="true"') == 2
    assert html.count('aria-pressed="false"') == 9
    assert 'aria-live="polite"' in html
    assert '<form id="nameForm"' in html
    assert '<label for="nameInput"' in html
    assert 'href="/"' in html
    for label in ("Temps", "Sans faute", "Erreurs", "Précision"):
        assert f"<dt>{label}</dt>" in html


def test_game_script_renders_remaining_flags_and_all_mode():
    script = (ROOT / "static/mapix/game.js").read_text()
    assert "session.remaining_flags" in script
    assert "document.createElement('button')" in script
    assert "submitAnswer('flag'" in script
    assert "submitAnswer('name'" in script
    assert "session.flag_done" in script
    assert "session.territory_done" in script
    assert "setAttribute('aria-label'" in script


def test_result_hides_perfect_metric_for_all_mode():
    script = (ROOT / "static/mapix/game.js").read_text()
    assert "resultPerfect" in script
    assert "state.session.mode === 'all'" in script
    assert "accuracy_percent" in script


def test_all_mode_refocuses_name_input_after_request_unlock():
    script = (ROOT / "static/mapix/game.js").read_text()
    busy_handler = script[script.index("function setBusy") : script.index("function syncGameControls")]
    assert busy_handler.index("syncGameControls();") < busy_handler.index("ui.nameInput.focus();")


def test_mapix_frontend_does_not_persist_game_results():
    sources = "\n".join(
        (ROOT / path).read_text()
        for path in ("static/mapix/game.js", "templates/mapix/index.html")
    )
    assert "localStorage" not in sources
    assert "sessionStorage" not in sources
    assert "indexedDB" not in sources


def test_world_svg_matches_all_catalog_countries():
    countries = json.loads((ROOT / "static/mapix/countries.json").read_text())
    root = ET.parse(ROOT / "static/mapix/world.svg").getroot()
    shapes = [n.attrib["data-country"] for n in root.iter() if "data-country" in n.attrib]
    targets = {n.attrib["data-target-country"] for n in root.iter() if "data-target-country" in n.attrib}
    assert {c["id"] for c in countries} == set(shapes) | targets
    assert shapes == sorted(set(shapes))


def test_svg_is_local_interactive_data_not_an_external_map():
    svg = (ROOT / "static/mapix/world.svg").read_text()
    assert SVG_NAMESPACE in svg
    local_content = svg.replace(SVG_NAMESPACE, "", 1)
    assert "http://" not in local_content
    assert "https://" not in local_content
    assert "xlink:href" not in svg
    assert "<script" not in svg
    assert 'viewBox="0 0 3600 1800"' in svg
    assert len(svg.encode()) < 4 * 1024 * 1024
    root = ET.fromstring(svg)
    assert {n.tag.rsplit("}", 1)[-1] for n in root.iter()} <= {"svg", "g", "path", "circle"}
    assert all(not k.lower().startswith("on") for n in root.iter() for k in n.attrib)


def test_natural_earth_license_is_packaged():
    text = (ROOT / "static/mapix/NATURAL_EARTH_LICENSE.txt").read_text()
    assert "public domain" in text.lower()
    assert "naturalearthdata.com" in text


def feature(code, coordinates, geometry_type="Polygon", name="Example"):
    return {"type": "Feature", "properties": {"ISO3166-1-Alpha-2": code, "name": name},
            "geometry": {"type": geometry_type, "coordinates": coordinates}}


def generate(tmp_path, features, codes):
    source = tmp_path / "source.geojson"
    catalog = tmp_path / "countries.json"
    output = tmp_path / "world.svg"
    source.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    catalog.write_text(json.dumps([{"id": c} for c in codes]))
    result = subprocess.run([sys.executable, str(ROOT / "tools/build_mapix_map.py"),
                             str(source), str(catalog), str(output)], capture_output=True, text=True)
    return result, output


def test_converter_projects_merges_simplifies_and_retains_holes(tmp_path):
    outer = [[0, 0], [1, 0.01], [2, 0], [2, 2], [0, 2], [0, 0]]
    hole = [[0.5, 0.5], [1, 0.5], [1, 1], [0.5, 0.5]]
    island = [[10, 0], [10.1, 0], [10.1, 0.1], [10, 0]]
    features = [feature("ZZ", [outer]), feature("FR", [outer, hole]),
                feature("FR", [[island]], "MultiPolygon")]
    result, output = generate(tmp_path, features, ["FR"])
    assert result.returncode == 0, result.stderr
    first = output.read_bytes()
    path = next(n for n in ET.fromstring(first).iter() if "data-country" in n.attrib)
    assert path.attrib["data-country"] == "FR"
    assert path.attrib["fill-rule"] == "evenodd"
    assert path.attrib["d"].count("M") == 3
    assert "1800.0,900.0" in path.attrib["d"]
    assert "1820.0,880.0" in path.attrib["d"]
    assert "1810.0,899.9" not in path.attrib["d"]
    assert len([n for n in ET.fromstring(first).iter() if "data-target-country" in n.attrib]) == 0
    result, output = generate(tmp_path, list(reversed(features)), ["FR"])
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == first


def test_converter_enlarges_small_country_at_largest_polygon(tmp_path):
    tiny = [[20, 0], [20.001, 0], [20.001, 0.001], [20, 0]]
    main = [[0, 0], [0.2, 0], [0.2, 0.2], [0, 0.2], [0, 0]]
    result, output = generate(tmp_path, [feature("VA", [[tiny], [main]], "MultiPolygon")], ["VA"])
    assert result.returncode == 0, result.stderr
    root = ET.parse(output).getroot()
    target = next(n for n in root.iter() if "data-target-country" in n.attrib)
    assert target.attrib.items() >= {"data-target-country": "VA", "cx": "1801.0",
                                     "cy": "899.0", "r": "7.0", "fill": "transparent"}.items()
    path = next(n for n in root.iter() if "data-country" in n.attrib)
    for ring in path.attrib["d"].split("M")[1:]:
        assert len(set(re.findall(r"\d+\.\d,\d+\.\d", ring))) >= 3


@pytest.mark.parametrize("features,codes", [([], ["FR"]),
    ([feature("FR", [], "Point")], ["FR"]),
    ([feature("-99", [], name="France")], ["FR", "NO"]),
])
def test_converter_fails_without_complete_valid_geometry(tmp_path, features, codes):
    result, output = generate(tmp_path, features, codes)
    assert result.returncode != 0
    assert not output.exists()
    assert "FR" in result.stderr


def test_converter_repairs_only_known_missing_natural_earth_iso_codes(tmp_path):
    ring = [[[0, 0], [2, 0], [2, 2], [0, 0]]]
    features = [feature("-99", ring, name="France"), feature("-99", ring, name="Norway")]
    result, output = generate(tmp_path, features, ["FR", "NO"])
    assert result.returncode == 0, result.stderr
    assert {n.attrib["data-country"] for n in ET.parse(output).getroot().iter()
            if "data-country" in n.attrib} == {"FR", "NO"}
    result, _ = generate(tmp_path, features + [features[0]], ["FR", "NO"])
    assert result.returncode != 0
