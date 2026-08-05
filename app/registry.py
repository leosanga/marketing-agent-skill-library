from dataclasses import dataclass


@dataclass
class Skill:
    name: str
    description: str
    args_schema: dict
    source_code: str
    func: callable


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[Skill]:
        return list(self._skills.values())

    def has(self, name: str) -> bool:
        return name in self._skills
