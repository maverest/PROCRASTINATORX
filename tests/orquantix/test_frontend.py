from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_native_width_keeps_orca_inside_the_control_column():
    css = (ROOT / "static/orquantix/style.css").read_text()
    native_width_rules = css[css.index("@media (max-width: 720px)") :]

    assert ".game-controls .orca-avatar" in native_width_rules
    assert "width: 72px;" in native_width_rules
    assert ".game-controls .orca-dialog" in native_width_rules
    assert "min-width: 0;" in native_width_rules


def test_guess_input_can_shrink_beside_the_submit_button():
    css = (ROOT / "static/orquantix/style.css").read_text()
    guess_input_rules = css[
        css.index(".guess-input {") : css.index(".guess-input::placeholder")
    ]

    assert "min-width: 0;" in guess_input_rules
