from enum import Enum


class TipoEspaco(str, Enum):
    PESSOAL = "PESSOAL"
    COMPARTILHADO = "COMPARTILHADO"


class PapelMembro(str, Enum):
    DONO = "DONO"
    ADMIN = "ADMIN"
    MEMBRO = "MEMBRO"


class TipoConta(str, Enum):
    BANCO = "BANCO"
    CARTEIRA = "CARTEIRA"


class AmbienteFinanceiro(str, Enum):
    PESSOAL = "PESSOAL"
    MOTORISTA = "MOTORISTA"
