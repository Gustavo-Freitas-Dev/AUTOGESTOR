"""
app/services/auth_service.py
───────────────────────────────
Lógica de autenticação: hash de senha, geração e validação de JWT.

DEPENDÊNCIAS NOVAS que você precisa instalar:
    uv add passlib[bcrypt] python-jose[cryptography]

  passlib[bcrypt]        → hash seguro de senha (nunca guardamos senha em texto puro)
  python-jose[cryptography] → criação e validação de tokens JWT
"""

import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.usuario_model import Usuario

# ── CONFIGURAÇÃO DO JWT ──────────────────────────────────────
#
# SECRET_KEY: chave usada para assinar o token. Quem não tiver
# essa chave não consegue forjar um token válido.
#
# IMPORTANTE: em produção, NUNCA deixe a chave hardcoded no código.
# Use uma variável de ambiente:
#   export AUTOGESTOR_SECRET_KEY="uma-chave-bem-grande-e-aleatoria"
# Aqui usamos os.getenv com um valor padrão só para o projeto
# funcionar imediatamente em desenvolvimento.
SECRET_KEY = os.getenv("AUTOGESTOR_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    warnings.warn(
        "AUTOGESTOR_SECRET_KEY não definida; usando chave temporária. "
        "Os logins serão invalidados quando o servidor reiniciar.",
        RuntimeWarning,
        stacklevel=2,
    )
ALGORITHM = "HS256"

# Tempo de validade do token. Depois disso, o usuário precisa
# fazer login de novo. 7 dias é um valor razoável para um app
# pessoal — ajuste conforme sua necessidade de segurança.
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias

# Contexto do passlib configurado para usar bcrypt — algoritmo
# de hash padrão da indústria para senhas (lento de propósito,
# o que dificulta ataques de força bruta).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt de uma senha em texto puro."""
    return pwd_context.hash(senha)


def verificar_senha(senha_texto: str, senha_hash: str) -> bool:
    """
    Compara a senha digitada no login com o hash salvo no banco.
    Retorna True se baterem, False caso contrário.
    Nunca comparamos string com string diretamente — o bcrypt
    cuida da comparação de forma segura (constant-time).
    """
    return pwd_context.verify(senha_texto, senha_hash)


def criar_access_token(dados: dict) -> str:
    """
    Gera um JWT assinado contendo os dados passados (geralmente
    {"sub": email_do_usuario}) mais a data de expiração.

    "sub" (subject) é o nome de campo padrão do JWT para identificar
    o dono do token.
    """
    to_encode = dados.copy()
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expira_em})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> int | None:
    """
    Valida o token e retorna o email do usuário (campo "sub") se
    o token for válido. Retorna None se o token for inválido,
    expirado ou adulterado.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        return int(subject) if subject is not None else None
    except (JWTError, TypeError, ValueError):
        return None


def buscar_usuario_por_email(db: Session, email: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.email == email).first()


def buscar_usuario_por_id(db: Session, usuario_id: int) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def autenticar_usuario(db: Session, email: str, senha: str) -> Usuario | None:
    """
    Fluxo completo de login: busca o usuário pelo email e confere
    a senha. Retorna o usuário se tudo bater, None caso contrário.

    Note que retornamos None tanto para "email não existe" quanto
    para "senha errada" — isso é proposital. Se a API respondesse
    mensagens diferentes para cada caso ("email não encontrado" vs
    "senha incorreta"), um atacante poderia descobrir quais emails
    estão cadastrados no sistema testando um por um. Por segurança,
    a mensagem de erro do login deve ser sempre genérica
    ("email ou senha incorretos").
    """
    usuario = buscar_usuario_por_email(db, email)
    if not usuario:
        return None
    if not verificar_senha(senha, usuario.senha_hash):
        return None
    return usuario
