from enum import StrEnum

from pydantic import BaseModel

from kitchensync.models import Recipe


class ParseStatus(StrEnum):
    SUCCESS = "success"
    NOT_IMPLEMENTED = "not_implemented"
    UNSUPPORTED_SOURCE = "unsupported_source"
    FAILED = "failed"


class ParseResult(BaseModel):
    recipe: Recipe | None = None
    status: ParseStatus
    source: str
    message: str | None = None
