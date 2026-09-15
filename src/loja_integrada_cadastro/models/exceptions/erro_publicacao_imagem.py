from __future__ import annotations


class ErroPublicacaoImagem(Exception):
    """Falha ao publicar uma foto no armazenamento remoto ou confirmar que ficou acessível.

    `chave_ou_url` é a chave publicada (falha no `publicar`) ou a URL conferida (falha no
    `existe`/HEAD) — o que identificar o recurso em cada caso.
    """

    def __init__(self, chave_ou_url: str, motivo: str) -> None:
        self.chave_ou_url = chave_ou_url
        self.motivo = motivo
        super().__init__(f"Falha ao publicar imagem '{chave_ou_url}': {motivo}")
