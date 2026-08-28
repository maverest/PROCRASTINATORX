from pathlib import Path


ROOT = Path(__file__).parents[2]
GAME_SCRIPT = ROOT / "static/calculatorx/game.js"
CHART_SCRIPT = ROOT / "static/calculatorx/chart.js"


def test_template_exposes_v2_panels_and_controls():
    html = (ROOT / "templates/calculatorx/index.html").read_text()

    for element_id in (
        "modePanel",
        "settingsPanel",
        "gamePanel",
        "resultPanel",
        "scoresPanel",
        "classicButton",
        "customButton",
        "constanceButton",
        "scoresButton",
        "resetClassicButton",
        "startCustomButton",
        "stopButton",
        "retryButton",
        "clearHistoryButton",
        "answerInput",
        "problemText",
        "timerValue",
        "scoreValue",
        "projectedScore",
        "responseChart",
        "operationSummaries",
        "resultError",
        "historyList",
    ):
        assert f'id="{element_id}"' in html
    assert 'aria-label="Arrêter la séance"' in html
    assert ">■<" in html
    assert '<script src="/static/calculatorx/chart.js" defer></script>' in html
    assert '<script src="/static/calculatorx/game.js" defer></script>' in html
    assert html.index('/static/calculatorx/chart.js') < html.index('/static/calculatorx/game.js')
    assert "<script>" not in html


def test_game_script_uses_absolute_deadline_and_round_token():
    script = GAME_SCRIPT.read_text()

    assert "performance.now()" in script
    assert "deadline" in script
    assert "roundToken" in script
    assert "requestAnimationFrame" in script
    assert "fetch('/games/calculatorx/session'" in script


def test_enter_shortcut_leaves_interactive_targets_to_native_behavior():
    script = GAME_SCRIPT.read_text()
    keydown_handler = script[script.index("document.addEventListener('keydown'") :]
    interactive_guard = (
        "if (event.target.closest('a, button, input, select, textarea, "
        "[role=\"button\"]')) return;"
    )

    assert interactive_guard in keydown_handler
    assert keydown_handler.index(interactive_guard) < keydown_handler.index(
        "event.preventDefault();"
    )
    assert keydown_handler.index(interactive_guard) < keydown_handler.index(
        "prepareRound();"
    )


def test_script_tracks_per_problem_time_and_manual_stop():
    script = GAME_SCRIPT.read_text()

    assert "problemStartedAt" in script
    assert "elapsed_ms" in script
    assert "projectedScore" in script
    assert "stopButton.addEventListener" in script
    assert "ended_reason" in script


def test_chart_has_sliding_live_window_and_operation_palette():
    script = CHART_SCRIPT.read_text()

    assert "samples.slice(-limit)" in script
    for operator in ("+", "−", "×", "÷"):
        assert repr(operator) in script or f"'{operator}'" in script


def test_panel_navigation_invalidates_a_pending_session_request():
    script = GAME_SCRIPT.read_text()
    cancel_handler = script[
        script.index("function cancelPreparation()") : script.index(
            "function navigateToPanel"
        )
    ]
    navigation_handler = script[
        script.index("function navigateToPanel") : script.index(
            "function clearError"
        )
    ]

    assert "++state.roundToken" in cancel_handler
    assert "setPreparing(false)" in cancel_handler
    assert navigation_handler.index("cancelPreparation();") < navigation_handler.index(
        "showPanel(panel);"
    )


def test_result_submission_error_is_rendered_inside_result_panel():
    html = (ROOT / "templates/calculatorx/index.html").read_text()
    script = GAME_SCRIPT.read_text()
    result_panel = html[html.index('id="resultPanel"') : html.index('id="scoresPanel"')]

    assert 'id="resultError"' in result_panel
    assert 'role="alert"' in result_panel
    assert "ui.resultError.textContent" in script


def test_game_style_is_speed_oriented_and_reduced_motion_safe():
    css = (ROOT / "static/calculatorx/style.css").read_text()

    assert "font-variant-numeric: tabular-nums" in css
    assert "#stopButton" in css
    assert ".range-group label:nth-of-type(3) { grid-column: 2; }" in css
    assert '.range-group > span[aria-hidden="true"]:nth-of-type(3) { grid-column: 3; }' in css
    assert ".range-group label:nth-of-type(4) { grid-column: 4; }" in css
    assert "label:nth-of-type(5)" not in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation: none" in css
