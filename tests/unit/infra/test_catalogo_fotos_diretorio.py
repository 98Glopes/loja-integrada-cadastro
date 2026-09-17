from pathlib import Path

from loja_integrada_cadastro.infra.catalogo_fotos_diretorio import CatalogoFotosDiretorio


def _criar_arquivo(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"fake")


def test_listar_aceita_extensoes_variadas_em_qualquer_caixa(tmp_path: Path) -> None:
    base = tmp_path / "3254002"
    _criar_arquivo(base / "b.JPG")
    _criar_arquivo(base / "a.jpeg")
    _criar_arquivo(base / "c.PNG")
    _criar_arquivo(base / "d.webp")
    _criar_arquivo(base / "e.HEIC")
    _criar_arquivo(base / "ignorado.txt")

    arquivos = CatalogoFotosDiretorio(tmp_path).listar("3254002")

    assert [arquivo.name for arquivo in arquivos] == [
        "a.jpeg",
        "b.JPG",
        "c.PNG",
        "d.webp",
        "e.HEIC",
    ]


def test_listar_devolve_lista_vazia_para_sku_pai_sem_pasta(tmp_path: Path) -> None:
    assert CatalogoFotosDiretorio(tmp_path).listar("inexistente") == []


def test_listar_devolve_lista_vazia_para_pasta_sem_arquivo_aceito(tmp_path: Path) -> None:
    _criar_arquivo(tmp_path / "3254002" / "notas.txt")

    assert CatalogoFotosDiretorio(tmp_path).listar("3254002") == []


def test_listar_ignora_subpastas(tmp_path: Path) -> None:
    _criar_arquivo(tmp_path / "3254002" / "a.jpg")
    _criar_arquivo(tmp_path / "3254002" / "antiga-subpasta" / "b.jpg")

    arquivos = CatalogoFotosDiretorio(tmp_path).listar("3254002")

    assert [arquivo.name for arquivo in arquivos] == ["a.jpg"]
