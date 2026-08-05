from app.registry import Skill, SkillRegistry

def test_register_and_get_skill():
    registry = SkillRegistry()
    skill = Skill(
        name="dummy_skill",
        description="A dummy skill for testing.",
        args_schema={},
        source_code="def dummy_skill():\n    return 'ok'",
        func=lambda: "ok",
    )
    registry.register(skill)

    fetched = registry.get("dummy_skill")
    assert fetched is not None
    assert fetched.func() == "ok"
    assert registry.has("dummy_skill")
    assert registry.has("nonexistent") is False

def test_list_skills_returns_all_registered():
    registry = SkillRegistry()
    for i in range(3):
        registry.register(Skill(
            name=f"skill_{i}", description="d", args_schema={}, source_code="", func=lambda: None,
        ))
    assert len(registry.list_skills()) == 3
