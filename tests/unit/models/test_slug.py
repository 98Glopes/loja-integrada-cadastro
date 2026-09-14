from __future__ import annotations

import pytest

from loja_integrada_cadastro.models.slug import slugificar


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Conjunto Baby Malha e Moletom", "conjunto-baby-malha-e-moletom"),
        ("Azul aço", "azul-aco"),
        ("  Legging!!  Cirre  ", "legging-cirre"),
        ("ABC123", "abc123"),
        ("", ""),
        ("---abc---", "abc"),
        ("É Único", "e-unico"),
    ],
)
def test_slugificar(texto: str, esperado: str) -> None:
    assert slugificar(texto) == esperado
