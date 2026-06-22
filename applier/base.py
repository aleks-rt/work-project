from dataclasses import dataclass


@dataclass
class ApplyResult:
    success: bool
    message: str


class BaseApplier:
    SOURCE = "unknown"

    def __init__(self, email: str, password: str, resume_path: str):
        self.email = email
        self.password = password
        self.resume_path = resume_path

    def apply(self, vacancy_url: str, vacancy_title: str) -> ApplyResult:
        raise NotImplementedError
