from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_split_layout_makes_orca_prominent_without_leaving_control_column():
    css = (ROOT / "static/orquantix/style.css").read_text()
    split_layout_rules = css[css.index("@media (min-width: 700px)") :]

    assert ".game-controls .orca-panel" in split_layout_rules
    assert "flex-direction: column;" in split_layout_rules
    assert ".game-controls .orca-avatar" in split_layout_rules
    assert "width: min(190px, 82%);" in split_layout_rules
    assert ".game-controls .orca-dialog" in split_layout_rules
    assert "min-width: 0;" in split_layout_rules
    assert ".game-controls .orca-bubble" in split_layout_rules
    assert "width: 100%;" in split_layout_rules


def test_guess_input_can_shrink_beside_the_submit_button():
    css = (ROOT / "static/orquantix/style.css").read_text()
    guess_input_rules = css[
        css.index(".guess-input {") : css.index(".guess-input::placeholder")
    ]

    assert "min-width: 0;" in guess_input_rules
