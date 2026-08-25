"""
app/schemas/usuario_schemas.py
─────────────────────────────────
Schemas Pydantic para autenticação.

Por que 3 schemas diferentes em vez de 1 só?
  CriarUsuario   → o que o frontend ENVIA no cadastro (tem senha em texto puro,
                   só nesse momento, pois ainda vai ser hasheada no service)
  LoginUsuario   → o que o frontend ENVIA no login (email + senha)
  UsuarioResposta → o que a API DEVOLVE — nunca inclui senha_hash nem senha,
                   só dados seguros de exibir (id, nome, email)

Separar assim evita o erro clássico de devolver a senha (ou o hash dela)
numa resposta JSON por descuido.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.services.auth_service import normalizar_email


class CriarUsuario(BaseModel):
    nome: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    # min_length=6 é uma validação básica de força de senha.
    # Pode reforçar depois (exigir número, maiúscula, etc) se quiser.
    senha: str = Field(..., min_length=6, max_length=72)

    @field_validator("email", mode="before")
    @classmethod
    def _normalizar_email(cls, valor: str) -> str:
        return normalizar_email(valor)


class LoginUsuario(BaseModel):
    email: EmailStr
    senha: str

    @field_validator("email", mode="before")
    @classmethod
    def _normalizar_email(cls, valor: str) -> str:
        return normalizar_email(valor)


class AtualizarUsuario(BaseModel):
    nome: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    senha_atual: str = Field(..., min_length=1, max_length=72)
    nova_senha: str | None = Field(default=None, min_length=6, max_length=72)

    @field_validator("email", mode="before")
    @classmethod
    def _normalizar_email(cls, valor: str) -> str:
        return normalizar_email(valor)


class UsuarioResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: EmailStr



class Token(BaseModel):
    """
    Schema de resposta do login/cadastro bem-sucedido.
    access_token → o JWT em si, que o frontend vai guardar
                   (localStorage) e reenviar em cada requisição
                   protegida no header Authorization.
    token_type   → sempre "bearer", é o padrão usado no header
                   Authorization: Bearer <token>
    usuario      → dados do usuário logado, para o frontend já
                   exibir o nome sem precisar de uma segunda requisição
    """
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResposta


class EsqueciSenhaRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def _normalizar_email(cls, valor: str) -> str:
        return normalizar_email(valor)


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    nova_senha: str = Field(..., min_length=6, max_length=72)
    confirmar_senha: str = Field(..., min_length=6, max_length=72)


class MensagemGenerica(BaseModel):
    message: str


class ExcluirContaRequest(BaseModel):
    senha_atual: str = Field(..., min_length=1, max_length=72)
