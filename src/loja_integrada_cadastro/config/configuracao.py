from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from loja_integrada_cadastro.config.leitor_ambiente import LeitorAmbiente
from loja_integrada_cadastro.models.exceptions.erro_configuracao import ErroConfiguracao


@dataclass(frozen=True)
class Configuracao:
    """Parâmetros da aplicação lidos de variáveis de ambiente (ARQUITETURA.md §11)."""

    anthropic_api_key: str | None = None
    llm_modelo_copywriter: str = "claude-opus-5"
    llm_modelo_seo: str = "claude-opus-5"
    llm_modelo_qa: str = "claude-opus-5"
    llm_effort_copywriter: str = "high"
    llm_effort_seo: str = "medium"
    llm_effort_qa: str = "medium"
    llm_max_tentativas_qa: int = 2
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    r2_url_publica: str | None = None
    imagem_lado_max_px: int = 1600
    imagem_tamanho_max_kb: int = 500
    produto_ativo: str = "S"
    peso_kg: Decimal = Decimal("0.1")
    altura_cm: Decimal = Decimal("4")
    largura_cm: Decimal = Decimal("22")
    comprimento_cm: Decimal = Decimal("22")
    loja_url: str = "https://www.kmilaamodas.com.br"
    lotes_dir: Path = Path("lotes")

    @classmethod
    def do_ambiente(cls, ambiente: Mapping[str, str] | None = None) -> Configuracao:
        """Monta a configuração a partir do ambiente; sem argumento, carrega `.env` do cwd."""
        if ambiente is None:
            load_dotenv(".env")
            ambiente = os.environ
        leitor = LeitorAmbiente(ambiente)
        padrao = cls()
        return cls(
            anthropic_api_key=leitor.opcional("ANTHROPIC_API_KEY"),
            llm_modelo_copywriter=leitor.texto(
                "LLM_MODELO_COPYWRITER", padrao.llm_modelo_copywriter
            ),
            llm_modelo_seo=leitor.texto("LLM_MODELO_SEO", padrao.llm_modelo_seo),
            llm_modelo_qa=leitor.texto("LLM_MODELO_QA", padrao.llm_modelo_qa),
            llm_effort_copywriter=leitor.texto(
                "LLM_EFFORT_COPYWRITER", padrao.llm_effort_copywriter
            ),
            llm_effort_seo=leitor.texto("LLM_EFFORT_SEO", padrao.llm_effort_seo),
            llm_effort_qa=leitor.texto("LLM_EFFORT_QA", padrao.llm_effort_qa),
            llm_max_tentativas_qa=leitor.inteiro(
                "LLM_MAX_TENTATIVAS_QA", padrao.llm_max_tentativas_qa
            ),
            r2_account_id=leitor.opcional("R2_ACCOUNT_ID"),
            r2_access_key_id=leitor.opcional("R2_ACCESS_KEY_ID"),
            r2_secret_access_key=leitor.opcional("R2_SECRET_ACCESS_KEY"),
            r2_bucket=leitor.opcional("R2_BUCKET"),
            r2_url_publica=leitor.opcional("R2_URL_PUBLICA"),
            imagem_lado_max_px=leitor.inteiro("IMAGEM_LADO_MAX_PX", padrao.imagem_lado_max_px),
            imagem_tamanho_max_kb=leitor.inteiro(
                "IMAGEM_TAMANHO_MAX_KB", padrao.imagem_tamanho_max_kb
            ),
            produto_ativo=leitor.sim_ou_nao("PRODUTO_ATIVO", padrao.produto_ativo),
            peso_kg=leitor.decimal("PESO_KG", padrao.peso_kg),
            altura_cm=leitor.decimal("ALTURA_CM", padrao.altura_cm),
            largura_cm=leitor.decimal("LARGURA_CM", padrao.largura_cm),
            comprimento_cm=leitor.decimal("COMPRIMENTO_CM", padrao.comprimento_cm),
            loja_url=leitor.texto("LOJA_URL", padrao.loja_url),
            lotes_dir=Path(leitor.texto("LOTES_DIR", str(padrao.lotes_dir))),
        )

    def exigir_anthropic(self) -> str:
        """Devolve a chave da API Anthropic ou falha nomeando a variável ausente."""
        if self.anthropic_api_key is None:
            raise ErroConfiguracao("ANTHROPIC_API_KEY")
        return self.anthropic_api_key

    def exigir_r2(self) -> None:
        """Falha nomeando a primeira variável do Cloudflare R2 ausente."""
        variaveis = {
            "R2_ACCOUNT_ID": self.r2_account_id,
            "R2_ACCESS_KEY_ID": self.r2_access_key_id,
            "R2_SECRET_ACCESS_KEY": self.r2_secret_access_key,
            "R2_BUCKET": self.r2_bucket,
            "R2_URL_PUBLICA": self.r2_url_publica,
        }
        for variavel, valor in variaveis.items():
            if valor is None:
                raise ErroConfiguracao(variavel)
