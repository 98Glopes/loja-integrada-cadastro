from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)


def test_aprovado_e_verdadeiro_sem_problemas_mesmo_com_avisos() -> None:
    resultado = ResultadoValidacao(
        problemas=(),
        avisos=(ProblemaValidacao("3254002", "marca", "sem perfil próprio"),),
    )

    assert resultado.aprovado is True


def test_aprovado_e_falso_com_algum_problema() -> None:
    resultado = ResultadoValidacao(
        problemas=(ProblemaValidacao("3254002", "cor", "fora da lista mestre"),),
        avisos=(),
    )

    assert resultado.aprovado is False
