"""
app/routes/auth.py
─────────────────────
Rotas de cadastro e login. Segue o mesmo padrão visual do seu
movimentacoes.py (APIRouter com prefix, tags, summary, description).
"""

import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.auth_dependencies import obter_usuario_atual
from app.database.dependencies import get_db
from app.models.espaco_financeiro import EspacoFinanceiro
from app.models.membro_espaco import MembroEspaco
from app.models.movimentacao import Movimentacao
from app.models.password_reset_token import PasswordResetToken
from app.models.usuario_model import Usuario
from app.schemas.usuario_schemas import (
    AtualizarUsuario,
    CriarUsuario,
    EsqueciSenhaRequest,
    ExcluirContaRequest,
    LoginUsuario,
    MensagemGenerica,
    RedefinirSenhaRequest,
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
    validar_requisitos_senha,
)
from app.services.email_service import PasswordResetEmailPayload, get_email_service
from app.services.espaco_service import criar_espaco_pessoal
from app.services.password_reset_service import (
    criar_token_recuperacao,
    localizar_usuario_por_email,
    mensagem_generica_recuperacao,
    montar_link_recuperacao,
    redefinir_senha_com_token,
)
from app.services.rate_limit_service import rate_limiter

router = APIRouter(prefix="/auth", tags=["Autenticação"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post(
    "/cadastro",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuário",
    description="Cria um usuário no banco de dados com senha hasheada e retorna um token JWT já autenticado",
)
def cadastrar(
    dado: CriarUsuario,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    metricas_ms: dict[str, float] = {}
    request_id = getattr(request.state, "request_id", "n/a")

    def _medir(nome: str, fn):
        t0 = time.perf_counter()
        resultado = fn()
        metricas_ms[nome] = (time.perf_counter() - t0) * 1000
        return resultado

    try:
        email_normalizado = normalizar_email(str(dado.email))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        _medir("connection_ms", lambda: db.connection())
    except SQLAlchemyError as exc:
        logger.exception("Falha ao obter conexao de banco no cadastro", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unavailable",
        ) from exc

    # Verifica se já existe alguém com esse e-mail antes de tentar
    # inserir — evita estourar um erro de integridade do banco
    # (UNIQUE constraint) e permite uma mensagem de erro mais clara.
    try:
        usuario_existente = _medir("email_lookup_ms", lambda: buscar_usuario_por_email(db, email_normalizado))
    except SQLAlchemyError as exc:
        logger.exception("Falha de banco no lookup de e-mail do cadastro", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unavailable",
        ) from exc

    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está cadastrado.",
        )

    senha_hash = _medir("password_hash_ms", lambda: hash_senha(dado.senha))

    novo_usuario = Usuario(
        nome=dado.nome,
        email=email_normalizado,
        senha_hash=senha_hash,
    )

    db.add(novo_usuario)
    try:
        _medir(
            "insert_ms",
            lambda: (
                db.flush(),
                criar_espaco_pessoal(db, novo_usuario),
            ),
        )
        _medir("commit_ms", lambda: db.commit())
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        )
    except DBAPIError as exc:
        db.rollback()
        logger.exception("Falha de banco ao persistir cadastro", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unavailable",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Falha de banco ao persistir cadastro", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unavailable",
        ) from exc

    _medir("refresh_ms", lambda: db.refresh(novo_usuario))
    if not novo_usuario.id:
        logger.error("Cadastro sem ID apos commit", extra={"email_mask": mascarar_email(email_normalizado)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="user_not_persisted")

    # Já gera o token no cadastro, para o usuário "entrar" direto
    # sem precisar fazer login logo em seguida — boa prática de UX.
    token = _medir(
        "token_ms",
        lambda: criar_access_token({"sub": str(novo_usuario.id), "tv": int(novo_usuario.token_version or 0)}),
    )

    metricas_ms["endpoint_total_ms"] = (time.perf_counter() - started) * 1000
    request.state.server_timing = metricas_ms
    logger.info(
        "auth.signup.metrics request_id=%s total_ms=%.2f connection_ms=%.2f lookup_ms=%.2f hash_ms=%.2f insert_ms=%.2f commit_ms=%.2f refresh_ms=%.2f token_ms=%.2f",
        request_id,
        metricas_ms.get("endpoint_total_ms", 0.0),
        metricas_ms.get("connection_ms", 0.0),
        metricas_ms.get("email_lookup_ms", 0.0),
        metricas_ms.get("password_hash_ms", 0.0),
        metricas_ms.get("insert_ms", 0.0),
        metricas_ms.get("commit_ms", 0.0),
        metricas_ms.get("refresh_ms", 0.0),
        metricas_ms.get("token_ms", 0.0),
    )

    if request.app.state.enable_server_timing:
        response.headers["Server-Timing"] = ", ".join(
            [
                f"signup_connection;dur={metricas_ms.get('connection_ms', 0.0):.2f}",
                f"signup_lookup;dur={metricas_ms.get('email_lookup_ms', 0.0):.2f}",
                f"signup_hash;dur={metricas_ms.get('password_hash_ms', 0.0):.2f}",
                f"signup_insert;dur={metricas_ms.get('insert_ms', 0.0):.2f}",
                f"signup_commit;dur={metricas_ms.get('commit_ms', 0.0):.2f}",
                f"signup_refresh;dur={metricas_ms.get('refresh_ms', 0.0):.2f}",
                f"signup_token;dur={metricas_ms.get('token_ms', 0.0):.2f}",
                f"signup_total;dur={metricas_ms.get('endpoint_total_ms', 0.0):.2f}",
            ]
        )
        response.headers["X-Request-ID"] = request_id

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
    started = time.perf_counter()
    metricas_ms: dict[str, float] = {}

    def _medir(nome: str, fn):
        t0 = time.perf_counter()
        resultado = fn()
        metricas_ms[nome] = (time.perf_counter() - t0) * 1000
        return resultado

    try:
        email_normalizado = normalizar_email(str(dado.email))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    logger.info("Tentativa de login", extra={"email_mask": mascarar_email(email_normalizado)})

    try:
        usuario = _medir("auth_ms", lambda: autenticar_usuario(db, email_normalizado, dado.senha))
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

    token = _medir("token_ms", lambda: criar_access_token({"sub": str(usuario.id), "tv": int(usuario.token_version or 0)}))
    metricas_ms["endpoint_total_ms"] = (time.perf_counter() - started) * 1000
    logger.info(
        "auth.login.metrics auth_ms=%.2f token_ms=%.2f total_ms=%.2f",
        metricas_ms.get("auth_ms", 0.0),
        metricas_ms.get("token_ms", 0.0),
        metricas_ms.get("endpoint_total_ms", 0.0),
    )

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
        ok, erro_senha = validar_requisitos_senha(dado.nova_senha)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=erro_senha)
        usuario.senha_hash = hash_senha(dado.nova_senha)
        usuario.token_version = int(usuario.token_version or 0) + 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        )
    db.refresh(usuario)

    token = criar_access_token({"sub": str(usuario.id), "tv": int(usuario.token_version or 0)})
    return Token(access_token=token, usuario=usuario)


@router.post(
    "/esqueci-senha",
    response_model=MensagemGenerica,
    summary="Solicita redefinicao de senha",
)
def esqueci_senha(
    dado: EsqueciSenhaRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", "n/a")
    ip = request.client.host if request.client else "unknown"
    email_normalizado = normalizar_email(str(dado.email))

    if not rate_limiter.allow(
        f"pwd_reset_req_ip:{ip}",
        settings.password_reset_request_limit_per_ip,
        settings.password_reset_rate_limit_window_seconds,
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="too_many_requests")

    if not rate_limiter.allow(
        f"pwd_reset_req_email:{email_normalizado}",
        settings.password_reset_request_limit_per_email,
        settings.password_reset_rate_limit_window_seconds,
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="too_many_requests")

    mensagem = mensagem_generica_recuperacao()
    started = time.perf_counter()

    try:
        usuario = localizar_usuario_por_email(db, email_normalizado)
        if usuario:
            token = criar_token_recuperacao(db, usuario)
            db.commit()

            payload = PasswordResetEmailPayload(
                to_email=usuario.email,
                recipient_name=usuario.nome,
                reset_link=montar_link_recuperacao(token),
                expires_minutes=settings.password_reset_token_expire_minutes,
                request_id=request_id,
            )
            email_service = get_email_service()
            background_tasks.add_task(email_service.send_password_reset, payload)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("password_reset_request_db_error", extra={"request_id": request_id})
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        delay_target_ms = settings.password_reset_uniform_delay_ms
        if elapsed_ms < delay_target_ms:
            time.sleep((delay_target_ms - elapsed_ms) / 1000)

    return MensagemGenerica(message=mensagem)


@router.post(
    "/redefinir-senha",
    response_model=MensagemGenerica,
    summary="Redefine senha com token de recuperacao",
)
def redefinir_senha(
    dado: RedefinirSenhaRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", "n/a")
    ip = request.client.host if request.client else "unknown"

    if dado.nova_senha != dado.confirmar_senha:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="As senhas não coincidem.")

    ok, erro_senha = validar_requisitos_senha(dado.nova_senha)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=erro_senha)

    if not rate_limiter.allow(
        f"pwd_reset_confirm_ip:{ip}",
        settings.password_reset_confirm_limit_per_ip,
        settings.password_reset_rate_limit_window_seconds,
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="too_many_requests")

    try:
        sucesso, motivo = redefinir_senha_com_token(db, dado.token, dado.nova_senha)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database_unavailable") from exc

    if not sucesso:
        if motivo == "token_expired":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token_expired")
        logger.info("password_reset_invalid_token", extra={"request_id": request_id})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token_invalid")

    return MensagemGenerica(message="Senha redefinida com sucesso.")


@router.get("/me", response_model=UsuarioResposta, summary="Retorna o usuário autenticado")
def obter_perfil(usuario: Usuario = Depends(obter_usuario_atual)):
    return usuario


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Invalida a sessão no cliente")
def logout(_: Usuario = Depends(obter_usuario_atual)) -> None:
    return None


@router.delete(
    "/me",
    response_model=MensagemGenerica,
    summary="Exclui a conta do usuário autenticado",
)
def excluir_conta(
    dado: ExcluirContaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
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

    usuario_id = usuario.id
    espacos_criados_ids = [
        espaco_id
        for (espaco_id,) in db.query(EspacoFinanceiro.id).filter(EspacoFinanceiro.criado_por_id == usuario_id).all()
    ]

    try:
        db.query(PasswordResetToken).filter(PasswordResetToken.usuario_id == usuario_id).delete(
            synchronize_session=False
        )

        if espacos_criados_ids:
            db.query(Movimentacao).filter(Movimentacao.espaco_id.in_(espacos_criados_ids)).delete(
                synchronize_session=False
            )
            db.query(MembroEspaco).filter(MembroEspaco.espaco_id.in_(espacos_criados_ids)).delete(
                synchronize_session=False
            )
            db.query(EspacoFinanceiro).filter(EspacoFinanceiro.id.in_(espacos_criados_ids)).delete(
                synchronize_session=False
            )

        db.query(Movimentacao).filter(Movimentacao.criado_por_id == usuario_id).delete(synchronize_session=False)
        db.query(MembroEspaco).filter(MembroEspaco.usuario_id == usuario_id).delete(synchronize_session=False)
        db.query(Usuario).filter(Usuario.id == usuario_id).delete(synchronize_session=False)

        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unavailable",
        ) from exc

    return MensagemGenerica(message="Conta excluída com sucesso.")
