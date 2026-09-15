from loja_integrada_cadastro.models.textos_produto import TextosProduto


def test_como_mapa_devolve_as_4_chaves_pelos_nomes_dos_campos() -> None:
    textos = TextosProduto(
        titulo="[DUMMY] Conjunto kiki Botões P ao G",
        descricao_html="<h2>[DUMMY] título</h2>",
        seo_tag_title="Conjunto kiki",
        seo_tag_description="[DUMMY] meta description",
    )

    assert textos.como_mapa() == {
        "titulo": "[DUMMY] Conjunto kiki Botões P ao G",
        "descricao_html": "<h2>[DUMMY] título</h2>",
        "seo_tag_title": "Conjunto kiki",
        "seo_tag_description": "[DUMMY] meta description",
    }
