from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.auth_dependencies import obter_usuario_atual
from app.database.dependencies import get_db
from app.models.membro_espaco import MembroEspaco
from app.models.usuario_model import Usuario
from app.services.espaco_service import verificar_acesso_espaco


def obter_membro_espaco(
    espaco_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
) -> MembroEspaco:
    return verificar_acesso_espaco(usuario.id, espaco_id, db)
