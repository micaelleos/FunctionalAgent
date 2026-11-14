"""Serviço de conta com armazenamento em memória (F03-RF-05, RF-07, RF-08)."""

from datetime import UTC, datetime

import pytest

from app.core.auth import Identity
from app.services.account import AccountService
from tests.fakes import ALICE, BOB, MemoryStore

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def service(store: MemoryStore) -> AccountService:
    return AccountService(store, clock=lambda: T0)


@pytest.mark.req("F03-RF-05")
def test_perfil_criado_no_primeiro_acesso(service: AccountService, store: MemoryStore) -> None:
    profile = service.profile(ALICE)

    assert profile.display_name == "Alice"
    assert profile.email == "alice@teste.dev"
    assert profile.created_at == T0
    assert store.users["uid-alice"]["locale"] == "pt-BR"


def test_segundo_acesso_mantem_o_perfil_original(store: MemoryStore) -> None:
    AccountService(store, clock=lambda: T0).profile(ALICE)
    later = AccountService(store, clock=lambda: datetime(2027, 1, 1, tzinfo=UTC)).profile(ALICE)

    assert later.created_at == T0


def test_nome_cai_para_o_inicio_do_email(service: AccountService) -> None:
    sem_nome = Identity("uid-x", "xavier@teste.dev", True, None, "password")

    assert service.profile(sem_nome).display_name == "xavier"


@pytest.mark.req("F03-RF-07")
def test_export_traz_so_os_dados_do_usuario(service: AccountService) -> None:
    service.profile(ALICE)
    service.profile(BOB)

    data = service.export(ALICE)

    assert data["uid"] == "uid-alice"
    assert data["user"]["data"]["email"] == "alice@teste.dev"
    assert "bob" not in str(data)


@pytest.mark.req("F03-RF-08")
def test_exclusao_e_idempotente(service: AccountService, store: MemoryStore) -> None:
    service.profile(ALICE)

    assert service.delete(ALICE) == 1
    assert service.delete(ALICE) == 0
    assert "uid-alice" not in store.users
