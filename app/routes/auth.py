"""
app/routes/auth.py
─────────────────────
Rotas de cadastro e login. Segue o mesmo padrão visual do seu
movimentacoes.py (APIRouter com prefix, tags, summary, description).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.auth_dependencies import obter_usuario_atual
from app.database.dependencies import get_db
from app.models.usuario_model import Usuario
from app.schemas.usuario_schemas import (
    AtualizarUsuario,
    CriarUsuario,
    LoginUsuario,
    Token,
    UsuarioResposta,
)
from app.services.auth_service import (
    AuthServiceUnavailableError,
    autenticar_usuario,
    buscar_usuario_por_email,
    criar_access_token,
    hash_senha,
    mascarar_email,
    normalizar_email,
)
from app.services.espaco_service import criar_espaco_pessoal

router = APIRouter(prefix="/auth", tags=["Autenticação"])
logger = logging.getLogger(__name__)


@router.post(
    "/cadastro",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuário",
    description="Cria um usuário no banco de dados com senha hasheada e retorna um token JWT já autenticado",
)
def cadastrar(dado: CriarUsuario, db: Session = Depends(get_db)):
    try:
        email_normalizado = normalizar_email(str(dado.email))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Verifica se já existe alguém com esse e-mail antes de tentar
    # inserir — evita estourar um erro de integridade do banco
    # (UNIQUE constraint) e permite uma mensagem de erro mais clara.
    usuario_existente = buscar_usuario_por_email(db, email_normalizado)
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está cadastrado.",
        )

    novo_usuario = Usuario(
        nome=dado.nome,
        email=email_normalizado,
        senha_hash=hash_senha(dado.senha),  # nunca salvamos a senha em texto puro
    )

    db.add(novo_usuario)
    try:
        db.flush()
        criar_espaco_pessoal(db, novo_usuario)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Falha de banco ao persistir cadastro")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unavailable",
        ) from exc

    db.refresh(novo_usuario)
    if not novo_usuario.id:
        logger.error("Cadastro sem ID apos commit", extra={"email_mask": mascarar_email(email_normalizado)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="user_not_persisted")

    # Já gera o token no cadastro, para o usuário "entrar" direto
    # sem precisar fazer login logo em seguida — boa prática de UX.
    token = criar_access_token({"sub": str(novo_usuario.id)})

    return Token(
        access_token=token,
        usuario=UsuarioResposta.model_validate(novo_usuario),
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Autentica um usuário existente",
    description="Verifica e-mail e senha e retorna um token JWT válido por 7 dias",
)
def login(dado: LoginUsuario, db: Session = Depends(get_db)):
    try:
        email_normalizado = normalizar_email(str(dado.email))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    logger.info("Tentativa de login", extra={"email_mask": mascarar_email(email_normalizado)})

    try:
        usuario = autenticar_usuario(db, email_normalizado, dado.senha)
    except AuthServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_service_unavailable",
        ) from exc

    if not usuario:
        # Mensagem genérica de propósito — não revela se o e-mail
        # existe ou não no sistema (ver explicação em auth_service.py)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )

    token = criar_access_token({"sub": str(usuario.id)})

    return Token(access_token=token, usuario=usuario)


@router.put(
    "/me",
    response_model=Token,
    summary="Atualiza os dados do usuário autenticado",
)
def atualizar_perfil(
    dado: AtualizarUsuario,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    try:
        email_normalizado = normalizar_email(str(dado.email))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        autenticado = autenticar_usuario(db, usuario.email, dado.senha_atual)
    except AuthServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_service_unavailable",
        ) from exc

    if not autenticado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha atual incorreta.",
        )

    email_em_uso = buscar_usuario_por_email(db, email_normalizado)
    if email_em_uso and email_em_uso.id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        )

    usuario.nome = dado.nome.strip()
    usuario.email = email_normalizado
    if dado.nova_senha:
        usuario.senha_hash = hash_senha(dado.nova_senha)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        )
    db.refresh(usuario)

    token = criar_access_token({"sub": str(usuario.id)})
    return Token(access_token=token, usuario=usuario)


@router.get("/me", response_model=UsuarioResposta, summary="Retorna o usuário autenticado")
def obter_perfil(usuario: Usuario = Depends(obter_usuario_atual)):
    return usuario


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Invalida a sessão no cliente")
def logout(_: Usuario = Depends(obter_usuario_atual)) -> None:
    return None
