"Test for the text cleaner."

import pytest

from app.rag.ingestion.cleaner import clean_text

def test_clean_text_empty_string():
    """Empty or None inputs returnd empty string."""
    assert clean_text("")==""
    assert clean_text(None)==""

def test_clean_text_no_changes_nedded():
    "Already clean text passes through unchanged"
    assert clean_text("Hello world")=="Hello world"
    assert clean_text("  Hello world  ")=="Hello world" #strip works

def test_clean_text_collapses_whitespace():
    "Whitespace is normalized"
    assert clean_text("Hello   world")=="Hello world"
    assert clean_text("Hello\nworld")=="Hello world"
    assert clean_text("Hello\tworld")=="Hello world"
    assert clean_text("Hello\r\nworld")=="Hello world"
    
def test_clean_text_removes_control_characters():
    # Null byte
    assert clean_text("Hello\x00world")=="Helloworld"
    # Vertical tab, form feed etc.
    assert clean_text("Hello\x0b\x0c\x07world")=="Helloworld"
    # DEL character (127)
    assert clean_text("Hello\x7fworld")=="Helloworld"
    # But tab, newline, carraige return are kept and then normalized
    assert clean_text("Hello\tworld")=="Hello world"
    assert clean_text("Hello\nworld")=="Hello world"
    assert clean_text("Hello\rworld")=="Hello world"

def test_clean_text_mixed_dirty_input():
    "Realistic messy input form a pdf extraction."
    dirty="Title\x00\n\n  Chapter 1  \t\t\n\n  Content here.  \r\n\r\nEnd.\x1f"
    expected="Title Chapter 1 Content here. End."
    assert clean_text(dirty)==expected