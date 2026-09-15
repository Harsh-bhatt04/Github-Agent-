from typing import TypedDict


class AgentState(TypedDict):
    user_request: str
    files: list[str]
    approval: bool
    result: str