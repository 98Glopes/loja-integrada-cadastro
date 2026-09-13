import importlib


def test_pacote_importavel() -> None:
    assert importlib.import_module("loja_integrada_cadastro") is not None
