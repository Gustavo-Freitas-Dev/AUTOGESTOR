"""
app/database/auth_dependencies.py
─────────────────────────────────────
Dependency injetável do FastAPI que protege rotas exigindo um
token JWT válido no header Authorization.

USO em qualquer rota que precise de login:

    from app.database.auth_dependencies import obter_usuario_atual

    @router.get("/movimentacoes/")
    def listar(
        db: Session = Depends(get_db),
        usuario = Depends(obter_usuario_atual),   # ← exige login
    ):
        ...

O FastAPI injeta automaticamente o usuário autenticado em
`usuario`. Se o token for inválido/ausente/expirado, o FastAPI
já responde 401 antes mesmo da função da rota rodar — você não
precisa escrever nenhuma checagem manual dentro da rota.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.usuario_model import Usuario
from app.services.auth_service import buscar_usuario_por_id, decodificar_token

# OAuth2PasswordBearer só define DE ONDE o token deve ser lido
# (header "Authorization: Bearer <token>") e gera automaticamente
# o cadeado 🔒 nas rotas protegidas dentro do Swagger (/docs).
# tokenUrl aponta para a rota de login, usada pelo Swagger para
# o botão "Authorize" funcionar — não afeta o frontend HTML.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def obter_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    1. Recebe o token extraído automaticamente do header pelo FastAPI
    2. Decodifica e valida o JWT
    3. Busca o usuário correspondente no banco
    4. Se qualquer etapa falhar, lança 401 Unauthorized
    """
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    usuario_id = decodificar_token(token)
    if usuario_id is None:
        raise credenciais_invalidas

    usuario = buscar_usuario_por_id(db, usuario_id)
    if usuario is None:
        raise credenciais_invalidas

    return usuario
