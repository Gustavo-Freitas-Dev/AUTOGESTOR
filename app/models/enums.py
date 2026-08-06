from enum import Enum


class TipoEspaco(str, Enum):
    PESSOAL = "PESSOAL"
    COMPARTILHADO = "COMPARTILHADO"


class PapelMembro(str, Enum):
    DONO = "DONO"
    ADMIN = "ADMIN"
    MEMBRO = "MEMBRO"
