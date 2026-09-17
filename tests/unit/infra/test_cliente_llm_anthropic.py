"""Testes do conector Anthropic com um fake mínimo do SDK (sem mock de biblioteca).

`_SdkFake` reproduz só a superfície que o conector usa: `client.beta.messages.parse(**kwargs)`
devolvendo objetos com a mesma forma de `ParsedBetaMessage` (ou levantando as exceções reais
do SDK, construídas com respostas `httpx2` falsas).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import anthropic
import httpx2
import pydantic
import pytest

from loja_integrada_cadastro.infra.cliente_llm_anthropic import ClienteLlmAnthropic
from loja_integrada_cadastro.models.exceptions.erro_geracao_texto import ErroGeracaoTexto
from loja_integrada_cadastro.models.exceptions.erro_recursos import ErroRecursos
from loja_integrada_cadastro.models.mensagem_llm import MensagemLlm
from loja_integrada_cadastro.models.pedido_llm import PedidoLlm
from loja_integrada_cadastro.models.preco_modelo_llm import PrecoModeloLlm
from loja_integrada_cadastro.models.tabela_precos_llm import TabelaPrecosLlm


@dataclass(frozen=True)
class Problema:
    campo: str
    motivo: str


@dataclass(frozen=True)
class Veredicto:
    aprovado: bool
    problemas: tuple[Problema, ...]


@dataclass
class _Uso:
    input_tokens: int = 1_000
    output_tokens: int = 500
    cache_read_input_tokens: int | None = 4_000
    cache_creation_input_tokens: int | None = None


@dataclass
class _Detalhes:
    category: str | None
    explanation: str | None


@dataclass
class _BlocoTexto:
    text: str
    parsed_output: object = None
    type: str = "text"


@dataclass
class _Mensagem:
    content: list[_BlocoTexto]
    usage: _Uso = field(default_factory=_Uso)
    model: str = "claude-opus-5"
    stop_reason: str | None = "end_turn"
    stop_details: _Detalhes | None = None
    _request_id: str | None = "req_123"

    @property
    def parsed_output(self) -> object:
        for bloco in self.content:
            if bloco.type == "text" and bloco.parsed_output:
                return bloco.parsed_output
        return None


def _resposta_com(saida: object, **campos: object) -> _Mensagem:
    """Mensagem do SDK cujo único bloco de texto é o JSON de `saida` já validado."""
    texto = json.dumps(pydantic.TypeAdapter(type(saida)).dump_python(saida))
    return _Mensagem(content=[_BlocoTexto(text=texto, parsed_output=saida)], **campos)  # type: ignore[arg-type]


class _MessagesFake:
    def __init__(self, roteiro: list[object]) -> None:
        self._roteiro = list(roteiro)
        self.chamadas: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> object:
        self.chamadas.append(kwargs)
        proximo = self._roteiro.pop(0)
        if isinstance(proximo, BaseException):
            raise proximo
        if isinstance(proximo, _Mensagem):
            _validar_como_o_sdk(proximo, kwargs["output_format"])  # type: ignore[arg-type]
        return proximo


def _validar_como_o_sdk(mensagem: _Mensagem, esquema: type[object]) -> None:
    """O SDK valida o texto com `TypeAdapter(output_format).validate_json` dentro do `parse`."""
    for bloco in mensagem.content:
        if bloco.type == "text" and bloco.parsed_output is None:
            bloco.parsed_output = pydantic.TypeAdapter(esquema).validate_json(bloco.text)


class _SdkFake:
    def __init__(self, roteiro: list[object]) -> None:
        self.messages = _MessagesFake(roteiro)
        self.beta = self

    @property
    def chamadas(self) -> list[dict[str, object]]:
        return self.messages.chamadas


def _erro_http(classe: type[anthropic.APIStatusError], status: int) -> anthropic.APIStatusError:
    requisicao = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    resposta = httpx2.Response(status, request=requisicao, headers={"request-id": "req_err"})
    return classe(f"erro {status}", response=resposta, body={"error": {"message": "x"}})


def _erro_conexao() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    )


_TABELA = TabelaPrecosLlm(
    precos={
        "claude-opus-5": PrecoModeloLlm(
            entrada=Decimal("5"),
            saida=Decimal("25"),
            cache_leitura=Decimal("0.5"),
            cache_escrita=Decimal("6.25"),
        ),
        "claude-opus-4-8": PrecoModeloLlm(
            entrada=Decimal("1"),
            saida=Decimal("1"),
            cache_leitura=Decimal("1"),
            cache_escrita=Decimal("1"),
        ),
    },
    data_referencia=date(2026, 9, 16),
)

_PEDIDO = PedidoLlm(
    blocos_sistema=("regras fixas", "perfil da marca"),
    mensagens=(MensagemLlm("user", "<produto>vestido</produto>"),),
    modelo="claude-opus-5",
    effort="high",
    max_tokens=4096,
)

_VEREDICTO = Veredicto(aprovado=False, problemas=(Problema("titulo", "muito longo"),))


def _cliente(roteiro: list[object]) -> tuple[ClienteLlmAnthropic, _SdkFake]:
    sdk = _SdkFake(roteiro)
    return ClienteLlmAnthropic(sdk, _TABELA), sdk  # type: ignore[arg-type]


class TestPedidoEnviado:
    def test_system_em_blocos_com_cache_control_so_no_ultimo(self) -> None:
        cliente, sdk = _cliente([_resposta_com(_VEREDICTO)])

        cliente.gerar(_PEDIDO, Veredicto)

        assert sdk.chamadas[0]["system"] == [
            {"type": "text", "text": "regras fixas"},
            {"type": "text", "text": "perfil da marca", "cache_control": {"type": "ephemeral"}},
        ]

    def test_parametros_de_modelo_thinking_effort_fallbacks_e_esquema(self) -> None:
        cliente, sdk = _cliente([_resposta_com(_VEREDICTO)])

        cliente.gerar(_PEDIDO, Veredicto)

        chamada = sdk.chamadas[0]
        assert chamada["model"] == "claude-opus-5"
        assert chamada["max_tokens"] == 4096
        assert chamada["thinking"] == {"type": "adaptive"}
        assert chamada["output_config"] == {"effort": "high"}
        assert chamada["output_format"] is Veredicto
        assert chamada["fallbacks"] == "default"
        assert chamada["betas"] == ["server-side-fallback-2026-07-01"]
        assert chamada["messages"] == [{"role": "user", "content": "<produto>vestido</produto>"}]

    def test_historico_de_retry_vai_como_turnos_user_e_assistant(self) -> None:
        cliente, sdk = _cliente([_resposta_com(_VEREDICTO)])
        pedido = PedidoLlm(
            blocos_sistema=("regras",),
            mensagens=(
                MensagemLlm("user", "gere"),
                MensagemLlm("assistant", '{"titulo": "x"}'),
                MensagemLlm("user", "título tem 74 caracteres, limite 68"),
            ),
            modelo="claude-opus-5",
            effort="medium",
            max_tokens=1024,
        )

        cliente.gerar(pedido, Veredicto)

        assert [m["role"] for m in sdk.chamadas[0]["messages"]] == ["user", "assistant", "user"]

    def test_modelo_sem_preco_falha_antes_de_chamar_o_sdk(self) -> None:
        cliente, sdk = _cliente([_resposta_com(_VEREDICTO)])
        pedido = PedidoLlm(("s",), (MensagemLlm("user", "u"),), "claude-inexistente", "low", 100)

        with pytest.raises(ErroRecursos, match="claude-inexistente"):
            cliente.gerar(pedido, Veredicto)

        assert sdk.chamadas == []


class TestConversaoDaResposta:
    def test_saida_e_o_dataclass_aninhado_validado_pelo_sdk(self) -> None:
        texto = json.dumps({"aprovado": False, "problemas": [{"campo": "titulo", "motivo": "x"}]})
        cliente, _ = _cliente([_Mensagem(content=[_BlocoTexto(text=texto)])])

        resposta = cliente.gerar(_PEDIDO, Veredicto)

        assert resposta.saida == Veredicto(False, (Problema("titulo", "x"),))
        assert resposta.texto == texto
        assert resposta.modelo == "claude-opus-5"
        assert resposta.request_id == "req_123"
        assert resposta.stop_reason == "end_turn"

    def test_uso_e_custo_pela_tabela_do_modelo_pedido(self) -> None:
        uso = _Uso(
            input_tokens=1_500,
            output_tokens=1_000,
            cache_read_input_tokens=4_000,
            cache_creation_input_tokens=None,
        )
        cliente, _ = _cliente([_resposta_com(_VEREDICTO, usage=uso)])

        resposta = cliente.gerar(_PEDIDO, Veredicto)

        assert resposta.uso.tokens_entrada == 1_500
        assert resposta.uso.tokens_saida == 1_000
        assert resposta.uso.tokens_cache_leitura == 4_000
        assert resposta.uso.tokens_cache_escrita == 0
        assert resposta.uso.custo_usd_estimado == Decimal("0.0345")

    def test_custo_usa_a_tabela_do_modelo_que_respondeu_apos_fallback(self) -> None:
        uso = _Uso(input_tokens=1, output_tokens=1, cache_read_input_tokens=1)
        uso.cache_creation_input_tokens = 1
        cliente, _ = _cliente([_resposta_com(_VEREDICTO, usage=uso, model="claude-opus-4-8")])

        resposta = cliente.gerar(_PEDIDO, Veredicto)

        assert resposta.modelo == "claude-opus-4-8"
        assert resposta.uso.custo_usd_estimado == Decimal("0.000004")

    def test_resposta_fora_do_esquema_e_erro_retentavel(self) -> None:
        cliente, _ = _cliente([_Mensagem(content=[_BlocoTexto(text='{"aprovado": "talvez"}')])])

        with pytest.raises(ErroGeracaoTexto, match="fora do esquema Veredicto") as info:
            cliente.gerar(_PEDIDO, Veredicto)

        assert info.value.retentavel is True

    def test_resposta_sem_bloco_de_texto_e_erro_retentavel(self) -> None:
        cliente, _ = _cliente([_Mensagem(content=[])])

        with pytest.raises(ErroGeracaoTexto, match="sem bloco de texto") as info:
            cliente.gerar(_PEDIDO, Veredicto)

        assert info.value.retentavel is True


class TestStopReason:
    def test_max_tokens_repete_uma_vez_com_o_dobro(self) -> None:
        truncada = _resposta_com(_VEREDICTO, stop_reason="max_tokens")
        cliente, sdk = _cliente([truncada, _resposta_com(_VEREDICTO)])

        resposta = cliente.gerar(_PEDIDO, Veredicto)

        assert [c["max_tokens"] for c in sdk.chamadas] == [4096, 8192]
        assert resposta.stop_reason == "end_turn"

    def test_max_tokens_duas_vezes_falha_sem_retry(self) -> None:
        truncada = _resposta_com(_VEREDICTO, stop_reason="max_tokens")
        cliente, sdk = _cliente([truncada, truncada])

        with pytest.raises(ErroGeracaoTexto, match="truncada.*8192") as info:
            cliente.gerar(_PEDIDO, Veredicto)

        assert info.value.retentavel is False
        assert len(sdk.chamadas) == 2

    def test_refusal_com_detalhes_falha_sem_retry(self) -> None:
        recusa = _Mensagem(
            content=[],
            stop_reason="refusal",
            stop_details=_Detalhes(category="general_harms", explanation="conteúdo impróprio"),
        )
        cliente, _ = _cliente([recusa])

        with pytest.raises(ErroGeracaoTexto, match="general_harms.*conteúdo impróprio") as info:
            cliente.gerar(_PEDIDO, Veredicto)

        assert info.value.retentavel is False

    def test_refusal_sem_detalhes_falha_com_mensagem_generica(self) -> None:
        cliente, _ = _cliente([_Mensagem(content=[], stop_reason="refusal")])

        with pytest.raises(ErroGeracaoTexto, match="sem detalhes"):
            cliente.gerar(_PEDIDO, Veredicto)


class TestTraducaoDeErros:
    @pytest.mark.parametrize(
        ("erro", "retentavel", "trecho"),
        [
            (_erro_http(anthropic.AuthenticationError, 401), False, "ANTHROPIC_API_KEY"),
            (_erro_http(anthropic.BadRequestError, 400), False, "rejeitado pela API"),
            (_erro_http(anthropic.RateLimitError, 429), True, "limite de requisições"),
            (_erro_http(anthropic.InternalServerError, 500), True, "HTTP 500"),
            (_erro_http(anthropic.OverloadedError, 529), True, "HTTP 529"),
            (_erro_http(anthropic.NotFoundError, 404), False, "HTTP 404"),
            (_erro_conexao(), True, "falha de conexão"),
        ],
    )
    def test_cada_classe_do_sdk_vira_erro_geracao_texto(
        self, erro: Exception, retentavel: bool, trecho: str
    ) -> None:
        cliente, _ = _cliente([erro])

        with pytest.raises(ErroGeracaoTexto, match=trecho) as info:
            cliente.gerar(_PEDIDO, Veredicto)

        assert info.value.retentavel is retentavel
        assert info.value.__cause__ is erro

    def test_bad_request_cita_modelo_effort_e_max_tokens(self) -> None:
        cliente, _ = _cliente([_erro_http(anthropic.BadRequestError, 400)])

        with pytest.raises(ErroGeracaoTexto, match="claude-opus-5.*high.*4096"):
            cliente.gerar(_PEDIDO, Veredicto)
