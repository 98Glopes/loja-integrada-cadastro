from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerfilMarca:
    """Perfil de posicionamento de uma marca, em prosa, para os prompts dos agentes.

    `generico` sinaliza que a marca não tem perfil próprio e recebeu o texto de
    `recursos/marcas/_generico.md` (o relatório do lote avisa quando isso acontece).
    """

    marca: str
    texto: str
    generico: bool
