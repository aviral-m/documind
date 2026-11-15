import re
from dataclasses import dataclass, field

import pytest

TOKEN_PATTERN = re.compile(r"token=([A-Za-z0-9_\-]+)")


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str

    @property
    def token(self) -> str:
        match = TOKEN_PATTERN.search(self.body)
        assert match, "email body has no token link"
        return match.group(1)


@dataclass
class FakeSender:
    sent: list[SentEmail] = field(default_factory=list)

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append(SentEmail(to=to, subject=subject, body=body))


@pytest.fixture
def sender() -> FakeSender:
    return FakeSender()
