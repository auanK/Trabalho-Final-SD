# O POJO
from dataclasses import dataclass

@dataclass
class UserRecord:
    nickname: str
    name: str
    description: str

    def __repr__(self) -> str:
        return f"UserRecord(Nick: '{self.nickname}', Name: '{self.name}', Desc: '{self.description[:20]}...')"