"""
Cedar policy syntax validation.

Uses cedarpy (real Rust Cedar-engine bindings) to parse uploaded policy text.
This validates *syntax* only (is this well-formed Cedar), not schema-level
semantics (e.g. whether entity types/actions referenced actually exist in
your domain model) — that's a heavier, optional step (cedarpy.validate_policies)
that requires authoring and maintaining a Cedar schema. Noted as a future
extension in the design doc.
"""

from cedarpy import PolicySet


class CedarValidationError(Exception):
    """Raised when uploaded content is not a valid Cedar policy file."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_cedar_policy(content: bytes) -> str:
    """
    Validate that `content` is a well-formed Cedar policy file.

    Returns the decoded policy text on success.
    Raises CedarValidationError with an actionable message on failure.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise CedarValidationError(
            f"File is not valid UTF-8 text and cannot be a Cedar policy file: {e}"
        )

    if not text.strip():
        raise CedarValidationError("File is empty; a Cedar policy file must contain at least one policy.")

    try:
        PolicySet.from_str(text)
    except ValueError as e:
        # cedarpy raises ValueError with the underlying Cedar parser's
        # diagnostic message (line/col info included), so we pass it through.
        raise CedarValidationError(f"Invalid Cedar policy syntax: {e}")

    return text