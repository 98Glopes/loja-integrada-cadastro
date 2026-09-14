from __future__ import annotations

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.exceptions.erro_processamento_imagem import (
    ErroProcessamentoImagem,
)
from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.nomeador_fotos import NomeadorFotos, SeletorImagensPai
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.slug import slugificar
from loja_integrada_cadastro.services.ports.armazenamento_imagens import ArmazenamentoImagens
from loja_integrada_cadastro.services.ports.catalogo_fotos import CatalogoFotos
from loja_integrada_cadastro.services.ports.processador_imagem import ProcessadorImagem


class PipelineFotos:
    """Nomeia, comprime, grava e escolhe as fotos de um produto (`docs/ARQUITETURA.md` §5).

    Uma falha ao processar qualquer foto aborta o produto inteiro: nenhuma foto parcial é
    publicada/contada, `estado.registrar_erro_fotos()` é chamado e a exceção é relançada
    (reexecução é idempotente, pois os nomes são determinísticos).
    """

    def __init__(
        self,
        catalogo: CatalogoFotos,
        processador: ProcessadorImagem,
        armazenamento: ArmazenamentoImagens,
    ) -> None:
        self._catalogo = catalogo
        self._processador = processador
        self._armazenamento = armazenamento

    def processar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> list[FotoProduto]:
        """Processa todas as fotos do produto e registra o resultado em `estado`."""
        catalogo = self._catalogo.listar(produto.sku_pai)
        arquivos_por_cor = {slugificar(cor): arquivos for cor, arquivos in catalogo.items()}

        fotos: list[FotoProduto] = []
        try:
            for cor in produto.cores:
                arquivos = arquivos_por_cor.get(slugificar(cor), [])
                for ordem, arquivo in enumerate(arquivos, start=1):
                    nome = NomeadorFotos.nomear(produto, cor, ordem)
                    chave = f"produtos/{produto.sku_pai}/{nome}"
                    dados = self._processador.preparar(arquivo)
                    url = self._armazenamento.publicar(chave, dados)
                    fotos.append(
                        FotoProduto(
                            sku_pai=produto.sku_pai,
                            cor=cor,
                            ordem=ordem,
                            arquivo_origem=arquivo,
                            nome=nome,
                            chave=chave,
                            url=url,
                            bytes=len(dados),
                        )
                    )
        except ErroProcessamentoImagem:
            estado.registrar_erro_fotos()
            raise

        selecionadas = SeletorImagensPai.selecionar(fotos)
        urls_pai = tuple(foto.url for foto in selecionadas if foto.url is not None)
        estado.registrar_fotos(fotos=tuple(fotos), imagens_pai=urls_pai)
        return fotos
