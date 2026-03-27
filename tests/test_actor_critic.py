"""Tests for src/pylon/workflows/actor_critic.py — ActorCriticWorkflow."""

from pylon.models import ContractStatus, RouterContract
from pylon.workflows.actor_critic import (
    ActorCriticWorkflow,
    ActorProtocol,
    CriticProtocol,
    MAX_AC_CYCLES,
)


class MockActor(ActorProtocol):
    def __init__(self, outputs: list[tuple[str, RouterContract]]):
        self._outputs = iter(outputs)

    def act(self, task: str, feedback: str = "") -> tuple[str, RouterContract]:
        return next(self._outputs)


class MockCritic(CriticProtocol):
    def __init__(self, verdicts: list[RouterContract]):
        self._verdicts = iter(verdicts)

    def critique(self, actor_output: str, task: str) -> RouterContract:
        return next(self._verdicts)


class TestActorCriticWorkflow:
    def test_approved_on_first_cycle(self):
        actor = MockActor([
            ("search plan", RouterContract(status=ContractStatus.PLANNED, confidence=70.0)),
        ])
        critic = MockCritic([
            RouterContract(status=ContractStatus.APPROVED, confidence=80.0),
        ])
        wf = ActorCriticWorkflow(actor, critic)
        output, contract, cycles = wf.run("find companies")
        assert output == "search plan"
        assert contract.status == ContractStatus.APPROVED
        assert cycles == 1

    def test_approved_after_revision(self):
        actor = MockActor([
            ("plan v1", RouterContract(status=ContractStatus.PLANNED, confidence=60.0)),
            ("plan v2", RouterContract(status=ContractStatus.PLANNED, confidence=75.0)),
        ])
        critic = MockCritic([
            RouterContract(
                status=ContractStatus.REQUEST_CHANGES,
                confidence=40.0,
                kb_update_notes="Add more companies",
            ),
            RouterContract(status=ContractStatus.APPROVED, confidence=85.0),
        ])
        wf = ActorCriticWorkflow(actor, critic)
        output, contract, cycles = wf.run("find companies")
        assert output == "plan v2"
        assert contract.status == ContractStatus.APPROVED
        assert cycles == 2

    def test_escalates_after_max_cycles(self):
        actor_outputs = [
            (f"plan v{i+1}", RouterContract(status=ContractStatus.PLANNED, confidence=50.0))
            for i in range(MAX_AC_CYCLES)
        ]
        critic_verdicts = [
            RouterContract(status=ContractStatus.REQUEST_CHANGES, confidence=30.0)
            for _ in range(MAX_AC_CYCLES)
        ]
        actor = MockActor(actor_outputs)
        critic = MockCritic(critic_verdicts)
        wf = ActorCriticWorkflow(actor, critic)
        output, contract, cycles = wf.run("find companies")
        assert contract.status == ContractStatus.ESCALATE
        assert cycles == MAX_AC_CYCLES

    def test_blocking_actor_stops_immediately(self):
        actor = MockActor([
            ("", RouterContract(status=ContractStatus.BLOCKED, confidence=0.0, blocking=True)),
        ])
        critic = MockCritic([])  # Should never be called
        wf = ActorCriticWorkflow(actor, critic)
        output, contract, cycles = wf.run("find companies")
        assert contract.blocking is True
        assert cycles == 1
