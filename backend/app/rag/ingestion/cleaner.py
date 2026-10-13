import re

# Build a translation table tha maps that controls characters
# to none(delete) or a space

_CONTROL_CHARS={
    i: None for i in range(0x20)
}
_CONTROL_CHARS[0X7F]=None
_CONTROL_CHARS[9]="\t"
_CONTROL_CHARS[10]="\n"
_CONTROL_CHARS[13]="\r"

# Compile once: pattern that matches runs od white space
# (spaces,tabs,newlines etc)
_WHITESPACE_RE=re.compile(r"\s+")

def clean_text(text: str) -> str:
    """ 
    Clean raw extracted text

    Steps:
    1.Remove control characters (expect normal whitespace).
    2.Collapse any run of whitespace into a single space
    3.Strip leading/trailing whitespace.
    
    Args:
        text: The raw string to clean

    Returns:
        The cleaned string for embedding and storage.
    """
    if not text:
        return ""

    # Step1: strip control chars uisng the translation table
    # str.translate(table) replaces each char using the table mapping

    no_control=text.translate(_CONTROL_CHARS)

    # Step2: collapse whitespace runs
    normalized=_WHITESPACE_RE.sub(" ",no_control)

    # Step3" trim ends
    return normalized.strip()
    