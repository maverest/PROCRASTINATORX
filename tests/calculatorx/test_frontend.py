from pathlib import Path


ROOT = Path(__file__).parents[2]
GAME_SCRIPT = ROOT / "static/calculatorx/game.js"
CHART_SCRIPT = ROOT / "static/calculatorx/chart.js"


def test_template_exposes_v2_panels_and_controls():
    html = (ROOT / "templates/calculatorx/index.html").read_text()

    for element_id in (
        "modePanel",
        "settingsPanel",
        "readyPanel",
        "gamePanel",
        "resultPanel",
        "scoresPanel",
        "classicButton",
        "customButton",
        "constanceButton",
        "scoresButton",
        "resetClassicButton",
        "startCustomButton",
        "startButton",
        "readyBackButton",
        "stopButton",
        "chartToggleButton",
        "retryButton",
        "clearHistoryButton",
        "answerInput",
        "problemText",
        "timerValue",
        "scoreValue",
        "projectedScore",
        "responseChart",
        "responseFigure",
        "operationSummaries",
        "settingsError",
        "resultError",
        "historyList",
    ):
        assert f'id="{element_id}"' in html
    assert 'aria-label="Arrêter la séance"' in html
    assert ">■ Stop<" in html
    assert '<script src="/static/calculatorx/chart.js" defer></script>' in html
    assert '<script src="/static/calculatorx/game.js" defer></script>' in html
    assert html.index('/static/calculatorx/chart.js') < html.index('/static/calculatorx/game.js')
    assert "<script>" not in html


def test_home_groups_modes_online_scores_and_best_first_local_history():
    html = (ROOT / "templates/calculatorx/index.html").read_text()
    script = GAME_SCRIPT.read_text()
    mode_panel = html[html.index('id="modePanel"') : html.index('id="settingsPanel"')]
    mode_actions = mode_panel[
        mode_panel.index('class="mode-actions"') : mode_panel.index('class="online-score-row"')
    ]

    assert mode_actions.index('id="classicButton"') < mode_actions.index('id="constanceButton"')
    assert mode_actions.index('id="constanceButton"') < mode_actions.index('id="customButton"')
    assert 'id="scoresButton"' not in mode_actions
    assert mode_panel.index('id="scoresButton"') < mode_panel.index('id="historyList"')
    assert "sessions.slice().sort((left, right) =>" in script
    assert "right.score - left.score" in script


def test_mode_selection_opens_a_start_screen_before_requesting_a_session():
    script = GAME_SCRIPT.read_text()
    select_mode = script[script.index("function selectMode") : script.index("function handleAnswer")]
    start_handler = script[script.index("ui.startButton.addEventListener") :]

    assert "showReadyPanel();" in select_mode
    assert "prepareRound();" not in select_mode
    assert "ui.startButton.addEventListener('click', prepareRound);" in start_handler


def test_game_keeps_stop_below_the_answer_and_can_toggle_the_live_chart():
    html = (ROOT / "templates/calculatorx/index.html").read_text()
    script = GAME_SCRIPT.read_text()
    game_panel = html[html.index('id="gamePanel"') : html.index('id="resultPanel"')]

    assert game_panel.index('id="scoreValue"') < game_panel.index('id="timerValue"')
    assert game_panel.index('id="timerValue"') < game_panel.index('id="problemText"')
    assert game_panel.index('id="answerInput"') < game_panel.index('id="stopButton"')
    assert game_panel.index('id="stopButton"') < game_panel.index('id="responseFigure"')
    assert "function setLiveChartVisible" in script
    assert "ui.chartToggleButton.addEventListener" in script


def test_custom_actions_share_one_framed_footer():
    html = (ROOT / "templates/calculatorx/index.html").read_text()
    settings_panel = html[html.index('id="settingsPanel"') : html.index('id="readyPanel"')]
    actions = settings_panel[
        settings_panel.index('class="settings-actions"') : settings_panel.index('</div>', settings_panel.index('class="settings-actions"'))
    ]

    assert 'id="settingsBackButton"' in actions
    assert 'id="resetClassicButton"' in actions
    assert 'id="startCustomButton"' in actions


def test_custom_duration_places_its_unit_after_the_value():
    html = (ROOT / "templates/calculatorx/index.html").read_text()
    duration = html[html.index('class="duration-field"') : html.index('</label>', html.index('class="duration-field"'))]

    assert duration.index('id="customDuration"') < duration.index('<span aria-hidden="true">s</span>')


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


def test_custom_errors_stay_in_settings_and_name_the_invalid_control():
    html = (ROOT / "templates/calculatorx/index.html").read_text()
    script = GAME_SCRIPT.read_text()
    settings_panel = html[html.index('id="settingsPanel"') : html.index('id="gamePanel"')]

    assert 'id="settingsError"' in settings_panel
    assert 'role="alert"' in settings_panel
    assert "showSettingsError" in script
    assert "focusSettingsField" in script
    assert "showPanel(ui.settings)" in script


def test_result_summary_renders_zero_count_entries_for_enabled_operations():
    script = GAME_SCRIPT.read_text()

    assert "state.config.operations" in script
    assert "count: 0" in script


def test_history_score_validation_uses_the_mode_specific_reserve_limit():
    script = GAME_SCRIPT.read_text()

    assert "function historyScoreLimit" in script
    assert "Math.ceil(512 * session.duration_seconds / 120)" in script
    assert "isIntegerInRange(session.score, 0, historyScoreLimit(session))" in script


def test_unstructured_session_errors_use_the_french_fallback_message():
    script = GAME_SCRIPT.read_text()
    catch_handler = script[script.index(".catch((error) => {") : script.index("  function selectMode")]

    assert "error instanceof SessionError" in catch_handler
    assert "Impossible de préparer la partie." in catch_handler


def test_scores_screen_loads_and_clears_local_history():
    script = GAME_SCRIPT.read_text()

    assert "fetch('/games/calculatorx/history')" in script
    assert "method: 'DELETE'" in script
    assert "window.confirm" in script


def test_successful_history_delete_invalidates_all_predelete_reads():
    script = GAME_SCRIPT.read_text()
    load_history = script[
        script.index("async function loadHistory()") : script.index("async function clearHistory()")
    ]
    clear_history = script[
        script.index("async function clearHistory()") : script.index("function numberFrom")
    ]

    assert "historyGeneration: 0" in script
    assert "const generation = state.historyGeneration;" in load_history
    assert "generation !== state.historyGeneration" in load_history
    assert "++state.historyGeneration;" in clear_history
    assert "if (!ui.mode.hidden) loadHistory();" in clear_history
    assert "token === state.historyToken && !ui.mode.hidden" in clear_history


def test_home_screen_exposes_an_accessible_history_error():
    html = (ROOT / "templates/calculatorx/index.html").read_text()
    mode_panel = html[html.index('id="modePanel"') : html.index('id="settingsPanel"')]

    assert 'id="historyError"' in mode_panel
    assert 'role="alert"' in mode_panel


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


def test_template_has_post_game_profile_picker_and_two_boards():
    html = (ROOT / "templates/calculatorx/index.html").read_text()

    for element_id in (
        "submitScoreButton",
        "profilePicker",
        "profileList",
        "newProfileInput",
        "createProfileButton",
        "classicLeaderboard",
        "constanceLeaderboard",
    ):
        assert f'id="{element_id}"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'id="profileCancelButton" type="button" aria-label="Fermer"' in html


def test_browser_uses_only_local_leaderboard_routes_and_two_modes():
    script = GAME_SCRIPT.read_text()

    assert "/games/calculatorx/leaderboard/submit" in script
    assert "/games/calculatorx/leaderboards/" in script
    assert "/games/calculatorx/profiles" in script
    assert "workers.dev" not in script
    assert "classic" in script
    assert "constance" in script


def test_pending_history_and_result_use_one_safe_profile_picker_flow():
    script = GAME_SCRIPT.read_text()

    assert "function openProfilePicker" in script
    assert "function closeProfilePicker" in script
    assert "submission_status === 'pending'" in script
    assert "leaderboard_eligible" in script
    assert "session_id: state.pendingSubmissionSessionId" in script
    assert "profile_id: profileId" in script
    assert "document.createElement('button')" in script
    assert "textContent" in script


def test_profile_picker_preserves_focus_and_prevents_duplicate_submissions():
    script = GAME_SCRIPT.read_text()

    assert "event.key === 'Escape'" in script
    assert "event.key !== 'Tab'" in script
    assert "state.submissionInFlight" in script
    assert "state.profileCreateInFlight" in script
    assert "trigger.focus()" in script


def test_hidden_profile_picker_does_not_cover_the_game():
    css = (ROOT / "static/calculatorx/style.css").read_text()

    assert ".profile-picker[hidden] { display: none; }" in css
