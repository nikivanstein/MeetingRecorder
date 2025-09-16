from meeting_recorder.app import build_label_map, format_action_items


def test_build_label_map_handles_empty_rows():
    labels = build_label_map([["SPEAKER_0", "Alice"], ["SPEAKER_1", ""], []])
    assert labels["SPEAKER_0"] == "Alice"
    assert labels["SPEAKER_1"] == "SPEAKER_1"


def test_format_action_items_formats_owner():
    markdown = format_action_items([
        {"description": "Follow up with client", "owner": "Bob"},
        {"description": ""},
    ])
    assert "Bob" in markdown
    assert "Follow up" in markdown
    assert "No action" not in markdown
