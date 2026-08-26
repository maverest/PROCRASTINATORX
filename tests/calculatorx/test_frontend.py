from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_template_exposes_three_panels_and_external_script():
    html = (ROOT / "templates/calculatorx/index.html").read_text()

    for element_id in (
        "welcomePanel",
        "gamePanel",
        "resultPanel",
        "startButton",
        "retryButton",
        "answerInput",
        "problemText",
        "timerValue",
        "scoreValue",
        "finalScore",
        "errorMessage",
    ):
        assert f'id="{element_id}"' in html
    assert '<script src="/static/calculatorx/game.js"></script>' in html
    assert "<script>" not in html


def test_game_script_uses_absolute_deadline_and_round_token():
    script = (ROOT / "static/calculatorx/game.js").read_text()

    assert "performance.now()" in script
    assert "deadline" in script
    assert "roundToken" in script
    assert "requestAnimationFrame" in script
    assert "fetch('/games/calculatorx/session'" in script


def test_enter_shortcut_leaves_interactive_targets_to_native_behavior():
    script = (ROOT / "static/calculatorx/game.js").read_text()
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


def test_styles_include_reduced_motion_fallback():
    css = (ROOT / "static/calculatorx/style.css").read_text()

    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation: none" in css
