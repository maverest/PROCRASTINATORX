import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).parents[2]
SVG_NAMESPACE = 'xmlns="http://www.w3.org/2000/svg"'
SVG_TAG = "{http://www.w3.org/2000/svg}svg"
REGION_TOTALS = {
    "africa": 54,
    "europe": 44,
    "asia": 48,
    "north-america": 23,
    "south-america": 12,
    "oceania": 14,
}


def test_template_exposes_mapix_panels_and_controls():
    html = (ROOT / "templates/mapix/index.html").read_text()
    for element_id in (
        "setupPanel", "gamePanel", "resultPanel", "fatalPanel",
        "modeChoices", "regionChoices", "playButton", "quitButton",
        "solutionButton",
        "retryButton", "menuButton", "mapContainer", "flagPanel", "flagGrid",
        "countryPrompt", "progressValue", "timerValue", "nameForm", "nameInput",
        "resultTime", "resultPerfect", "resultErrors", "resultAccuracy",
    ):
        assert f'id="{element_id}"' in html
    assert '<script src="/static/mapix/game.js" defer></script>' in html
    assert '<script src="/static/mapix/map.js" defer></script>' in html
    assert '<script src="/static/mapix/flags.js" defer></script>' in html
    assert (
        html.index('/static/mapix/map.js')
        < html.index('/static/mapix/flags.js')
        < html.index('/static/mapix/game.js')
    )
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
    for method in ("setRegion", "setInteractive", "setFound", "setRevealed", "flashWrong", "markCorrect", "destroy"):
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


def test_starting_a_game_resets_the_flag_panel_scroll_position():
    script = (ROOT / "static/mapix/game.js").read_text()
    start_game = script[script.index("async function startGame") : script.index("function handleAnswerError")]
    assert "ui.flagPanel.scrollTop = 0;" in start_game
    assert start_game.index("ui.flagPanel.scrollTop = 0;") < start_game.index("renderSession();")


def test_result_hides_perfect_metric_for_all_mode():
    script = (ROOT / "static/mapix/game.js").read_text()
    assert "resultPerfect" in script
    assert "state.session.mode === 'all'" in script
    assert "accuracy_percent" in script


def test_all_mode_refocuses_name_input_after_request_unlock():
    script = (ROOT / "static/mapix/game.js").read_text()
    busy_handler = script[script.index("function setBusy") : script.index("function syncGameControls")]
    assert busy_handler.index("syncGameControls();") < busy_handler.index("ui.nameInput.focus();")


def test_failed_catalog_load_can_be_retried_without_dropping_successful_cache():
    script = (ROOT / "static/mapix/game.js").read_text()
    loader = script[script.index("function loadCatalog") : script.index("function stopTimer")]
    assert ".catch(error => {" in loader
    assert "catalogPromise = null;" in loader
    assert "throw error;" in loader


def test_mapix_frontend_does_not_persist_game_results():
    sources = "\n".join(
        (ROOT / path).read_text()
        for path in ("static/mapix/game.js", "templates/mapix/index.html")
    )
    assert "localStorage" not in sources
    assert "sessionStorage" not in sources
    assert "indexedDB" not in sources


def test_solution_control_is_hidden_for_all_mode_and_calls_dedicated_route():
    html = (ROOT / "templates/mapix/index.html").read_text()
    script = (ROOT / "static/mapix/game.js").read_text()

    assert '<button id="solutionButton"' in html
    assert "ui.solutionButton.hidden = session.mode === 'all';" in script
    assert "fetch('/games/mapix/solution'" in script
    assert "question_index: state.session.question_index" in script
    assert "!state.session.solution_available" in script


def test_session_is_created_only_after_visible_map_is_ready():
    script = (ROOT / "static/mapix/game.js").read_text()
    start_game = script[script.index("async function startGame") : script.index("function handleAnswerError")]

    assert start_game.index("await loadCatalog();") < start_game.index("await state.map.ready;")
    assert start_game.index("await state.map.ready;") < start_game.index("fetch('/games/mapix/session'")


def test_all_mode_makes_country_shapes_noninteractive_but_keeps_map_navigation():
    game = (ROOT / "static/mapix/game.js").read_text()
    map_script = (ROOT / "static/mapix/map.js").read_text()
    css = (ROOT / "static/mapix/style.css").read_text()

    assert "state.map?.setInteractive" in game
    assert "session.mode !== 'all'" in game
    assert "function setInteractive" in map_script
    assert "removeAttribute('role')" in map_script
    assert "removeAttribute('tabindex')" in map_script
    assert "if (!interactive) return;" in map_script
    assert "ArrowLeft" in map_script and "wheel" in map_script
    assert '[role="button"].is-found' not in css
    assert ".map-svg .is-found" in css


def test_revealed_answers_and_imperfect_countries_have_distinct_visual_states():
    game = (ROOT / "static/mapix/game.js").read_text()
    map_script = (ROOT / "static/mapix/map.js").read_text()
    css = (ROOT / "static/mapix/style.css").read_text()

    assert "session.revealed_actions.includes('flag')" in game
    assert "state.map?.setRevealed" in game
    assert "session.imperfect" in game
    assert "classList.toggle('is-imperfect'" in map_script
    assert "classList.toggle('is-solution'" in map_script
    assert ".is-imperfect" in css
    assert ".is-solution" in css
    reduced = css[css.index("@media (prefers-reduced-motion: reduce)") :]
    assert ".is-solution" in reduced


def test_world_svg_matches_all_catalog_countries():
    countries = json.loads((ROOT / "static/mapix/countries.json").read_text())
    root = ET.parse(ROOT / "static/mapix/world.svg").getroot()
    shapes = [n.attrib["data-country"] for n in root.iter() if "data-country" in n.attrib]
    targets = {n.attrib["data-target-country"] for n in root.iter() if "data-target-country" in n.attrib}
    assert {c["id"] for c in countries} == set(shapes) | targets
    assert shapes == sorted(set(shapes))


def _interactive_points(node):
    if "d" in node.attrib:
        values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", node.attrib["d"])]
        return list(zip(values[::2], values[1::2]))
    return [(float(node.attrib["cx"]), float(node.attrib["cy"]))]


def test_each_region_initial_view_contains_a_usable_shape_or_target_for_every_country():
    rows = json.loads((ROOT / "static/mapix/countries.json").read_text())
    root = ET.parse(ROOT / "static/mapix/world.svg").getroot()
    wrap_x = float(root.attrib["data-wrap-x"])
    wrap_threshold = float(root.attrib["data-wrap-threshold"])
    points = {row["id"]: [] for row in rows}
    for node in root.iter():
        country_id = node.attrib.get("data-country") or node.attrib.get("data-target-country")
        if country_id:
            node_points = _interactive_points(node)
            points[country_id].extend(node_points)
            if any(x < wrap_threshold for x, _ in node_points):
                points[country_id].extend((x + wrap_x, y) for x, y in node_points)

    for region, expected_total in REGION_TOTALS.items():
        x, y, width, height = map(float, root.attrib[f"data-view-{region}"].split())
        region_rows = [row for row in rows if row["continent"] == region]
        assert len(region_rows) == expected_total
        missing = [
            row["id"] for row in region_rows
            if not any(x <= px <= x + width and y <= py <= y + height
                       for px, py in points[row["id"]])
        ]
        assert missing == [], f"{region}: {missing}"


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


def test_flag_icons_license_and_pinned_source_are_packaged():
    license_text = (ROOT / "static/mapix/FLAG_ICONS_LICENSE.txt").read_text()
    source_text = (ROOT / "static/mapix/FLAGS_SOURCE.md").read_text()
    assert "MIT License" in license_text
    assert "Panayiotis Lipiridis" in license_text
    assert "flag-icons 7.5.0" in source_text
    assert "5502d1bb0bda9f258d726d3c084a2d57a07cfdfa6d2ed18cbb5a1ee11b307778" in source_text


def test_every_catalog_country_has_a_safe_local_svg_flag():
    countries = json.loads((ROOT / "static/mapix/countries.json").read_text())
    flag_dir = ROOT / "static/mapix/flags"
    flag_files = sorted(flag_dir.glob("*.svg"))
    assert [path.stem for path in flag_files] == sorted(
        country["id"].lower() for country in countries
    )
    assert len(flag_files) == 195

    for path in flag_files:
        source = path.read_text(encoding="utf-8")
        root = ET.fromstring(source)
        assert root.tag == SVG_TAG, path.name
        assert root.attrib.get("viewBox"), path.name
        lowered = source.lower()
        assert "<script" not in lowered, path.name
        assert "javascript:" not in lowered, path.name
        content_without_namespaces = re.sub(r'xmlns(?::\w+)?="[^"]+"', "", source)
        assert "http://" not in content_without_namespaces, path.name
        assert "https://" not in content_without_namespaces, path.name
        assert all(
            not (
                key.rsplit("}", 1)[-1] == "href"
                and not value.startswith("#")
            )
            for node in root.iter()
            for key, value in node.attrib.items()
        ), path.name
        assert all(
            not key.lower().startswith("on")
            for node in root.iter()
            for key in node.attrib
        ), path.name


def test_flag_image_factory_contract_is_local_accessible_and_has_no_emoji():
    factory = (ROOT / "static/mapix/flags.js").read_text()
    game = (ROOT / "static/mapix/game.js").read_text()

    assert "document.createElement('img')" in factory
    assert "`/static/mapix/flags/${country.id.toLowerCase()}.svg`" in factory
    assert "image.alt = '';" in factory
    assert "image.draggable = false;" in factory
    assert "image.setAttribute('aria-hidden', 'true');" in factory
    assert "country.name" not in factory
    assert "country.flag" not in factory
    assert "button.append(window.MapixFlags.createImage(country));" in game
    assert "button.textContent = country.flag" not in game


def assert_physical_layers(root):
    groups = {node.attrib.get("id"): node for node in root.iter() if node.tag.endswith("g")}
    assert list(groups).index("mapix-relief") < list(groups).index("mapix-countries")
    assert list(groups).index("mapix-lakes") < list(groups).index("mapix-countries")
    for layer_id in ("mapix-relief", "mapix-lakes"):
        layer = groups[layer_id]
        assert layer.attrib.get("pointer-events") == "none"
        assert len(list(layer)) >= 4
        assert all(
            "data-country" not in node.attrib
            and "data-target-country" not in node.attrib
            for node in layer.iter()
        )


def test_packaged_map_contains_non_interactive_physical_layers_below_countries():
    assert_physical_layers(ET.parse(ROOT / "static/mapix/world.svg").getroot())


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


def test_converter_always_emits_safe_physical_layers_below_countries(tmp_path):
    ring = [[[0, 0], [2, 0], [2, 2], [0, 0]]]
    result, output = generate(tmp_path, [feature("FR", ring)], ["FR"])
    assert result.returncode == 0, result.stderr
    assert_physical_layers(ET.parse(output).getroot())


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
