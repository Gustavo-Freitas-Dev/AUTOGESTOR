
/*
  URL DA API — DINÂMICA, NÃO MAIS FIXA
  ════════════════════════════════════════
  ANTES: const API = 'http://127.0.0.1:8000/movimentacoes';

  PROBLEMA: 127.0.0.1 significa "esta mesma máquina". No PC
  funcionava porque navegador e API estavam no mesmo lugar.
  No celular, 127.0.0.1 aponta pro PRÓPRIO CELULAR — que não
  tem a API rodando nele. Por isso o fetch falhava sempre,
  mesmo com o ngrok ativo e funcionando.

  SOLUÇÃO: usar window.location.origin, que pega automaticamente
  o protocolo + domínio + porta de onde ESTA PÁGINA foi carregada.

  Isso só funciona de forma 100% confiável se o HTML for servido
  PELA PRÓPRIA API (ex: app/static/autogestor.html, acessado via
  http://SEU-NGROK.ngrok.io/static/autogestor.html) — assim a
  origem da página e a origem da API são exatamente a mesma,
  sem precisar de CORS nem de configurar URL nenhuma na mão.

  Se você abrir o HTML como arquivo local (file://) em vez de
  servido pela API, window.location.origin não vai funcionar
  (vira "null" ou "file://") — nesse caso, descomente a linha
  FALLBACK_MANUAL abaixo e troque pela URL do seu ngrok atual.
*/
// FALLBACK_MANUAL: const API = 'https://SEU-LINK-NGROK.ngrok-free.app/movimentacoes';
let API = '';
let ESPACOS = [];
let ESPACO_ATUAL = null;
let ESPACO_EM_EDICAO = null;
let TOKEN = localStorage.getItem('autogestor_token');
let USUARIO = null;
let FOTO_TEMP = null;
try {
  USUARIO = JSON.parse(localStorage.getItem('autogestor_usuario') || 'null');
} catch (_) {
  localStorage.removeItem('autogestor_usuario');
}
if (USUARIO?.id) {
  USUARIO.foto = localStorage.getItem(`autogestor_foto_${USUARIO.id}`) || null;
}

if (!TOKEN) {
  window.location.replace('/static/login.html');
}

const AUTH_FAILURE_DETAILS = new Set(['token_missing', 'token_invalid', 'token_expired', 'user_not_found']);

function tokenAtualSessao() {
  return localStorage.getItem('autogestor_token') || TOKEN || '';
}

function limparSessaoAutogestor() {
  localStorage.removeItem('autogestor_token');
  localStorage.removeItem('autogestor_usuario');
}

function encerrarSessaoExpirada() {
  localStorage.setItem('autogestor_return_to', window.location.pathname + window.location.search + window.location.hash);
  limparSessaoAutogestor();
  window.location.replace('/static/login.html');
}

function detalheErro(corpo) {
  if (!corpo) return null;
  if (typeof corpo.detail === 'string') return corpo.detail;
  if (Array.isArray(corpo.detail)) {
    return corpo.detail.map(item => item.msg || JSON.stringify(item)).join(', ');
  }
  if (Array.isArray(corpo.errors)) {
    return corpo.errors.map(item => item.msg || JSON.stringify(item)).join(', ');
  }
  return null;
}

function mensagemHttp(status, corpo, fallback) {
  const detalhe = detalheErro(corpo);
  if (detalhe) return detalhe;
  if (status === 400) return 'Não foi possível concluir a operação.';
  if (status === 401) return 'Sua sessão expirou. Entre novamente.';
  if (status === 403) return 'Você não possui permissão para executar esta ação.';
  if (status === 404) return 'Recurso não encontrado.';
  if (status === 409) return 'Conflito ao processar a solicitação.';
  if (status === 422) return 'Dados inválidos. Revise os campos e tente novamente.';
  if (status >= 500) return 'Erro interno da API. Tente novamente em instantes.';
  return fallback || `Erro ${status}`;
}

function deslogar() {
  const finalizar = () => {
    limparSessaoAutogestor();
    window.location.replace('/static/login.html');
  };

  fetch(window.location.origin + '/auth/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${tokenAtualSessao()}` },
  }).finally(finalizar);
}

function iniciaisDoNome(nome) {
  const partes = String(nome || 'Usuário').trim().split(/\s+/).filter(Boolean);
  return (partes[0]?.[0] || 'U') + (partes.length > 1 ? partes.at(-1)[0] : '');
}

function atualizarPerfilNoHeader() {
  document.getElementById('usuario-logado').textContent = USUARIO?.nome || 'Minha conta';
  document.getElementById('usuario-email').textContent = USUARIO?.email || '';
  const foto = document.getElementById('profile-foto');
  const iniciais = document.getElementById('profile-iniciais');
  iniciais.textContent = iniciaisDoNome(USUARIO?.nome).toUpperCase();
  foto.hidden = !USUARIO?.foto;
  iniciais.hidden = Boolean(USUARIO?.foto);
  if (USUARIO?.foto) foto.src = USUARIO.foto;
}

function atualizarPreviaFoto() {
  const foto = document.getElementById('foto-preview-img');
  const iniciais = document.getElementById('foto-preview-iniciais');
  iniciais.textContent = iniciaisDoNome(document.getElementById('conta-nome').value || USUARIO?.nome).toUpperCase();
  foto.hidden = !FOTO_TEMP;
  iniciais.hidden = Boolean(FOTO_TEMP);
  if (FOTO_TEMP) foto.src = FOTO_TEMP;
}

function selecionarFoto(event) {
  const arquivo = event.target.files?.[0];
  if (!arquivo) return;
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(arquivo.type)) {
    toast('Escolha uma imagem JPG, PNG ou WebP.', 'error');
    event.target.value = '';
    return;
  }
  if (arquivo.size > 2 * 1024 * 1024) {
    toast('A foto deve ter no máximo 2 MB.', 'error');
    event.target.value = '';
    return;
  }
  const leitor = new FileReader();
  leitor.onload = () => {
    FOTO_TEMP = leitor.result;
    atualizarPreviaFoto();
  };
  leitor.readAsDataURL(arquivo);
}

function removerFoto() {
  FOTO_TEMP = null;
  document.getElementById('conta-foto').value = '';
  atualizarPreviaFoto();
}

function fecharMenuPerfil() {
  document.getElementById('profile-dropdown').classList.remove('open');
  document.getElementById('profile-trigger').setAttribute('aria-expanded', 'false');
}

function fecharMenuExportacao() {
  document.getElementById('export-dropdown').classList.remove('open');
  document.getElementById('export-trigger').setAttribute('aria-expanded', 'false');
}

function alternarMenuExportacao(event) {
  event.stopPropagation();
  fecharMenuPerfil();
  fecharSeletorEspacos();
  const menu = document.getElementById('export-dropdown');
  const aberto = menu.classList.toggle('open');
  document.getElementById('export-trigger').setAttribute('aria-expanded', String(aberto));
}

function escolherExportacao(formato) {
  fecharMenuExportacao();
  if (formato === 'csv') exportarCSV();
  if (formato === 'excel') exportarExcel();
}

function alternarMenuPerfil(event) {
  event.stopPropagation();
  fecharMenuExportacao();
  fecharSeletorEspacos();
  const menu = document.getElementById('profile-dropdown');
  const aberto = menu.classList.toggle('open');
  document.getElementById('profile-trigger').setAttribute('aria-expanded', String(aberto));
}

function abrirMinhaConta() {
  fecharMenuPerfil();
  document.getElementById('conta-nome').value = USUARIO?.nome || '';
  document.getElementById('conta-email').value = USUARIO?.email || '';
  document.getElementById('conta-senha-atual').value = '';
  document.getElementById('conta-nova-senha').value = '';
  document.getElementById('conta-foto').value = '';
  FOTO_TEMP = USUARIO?.foto || null;
  atualizarPreviaFoto();
  document.getElementById('dialog-conta').showModal();
}

function abrirExcluirConta() {
  fecharMenuPerfil();
  document.getElementById('excluir-conta-senha').value = '';
  document.getElementById('dialog-excluir-conta').showModal();
}

function fecharMinhaConta() {
  document.getElementById('dialog-conta').close();
}

function fecharExcluirConta() {
  document.getElementById('dialog-excluir-conta').close();
}

async function salvarMinhaConta(event) {
  event.preventDefault();
  const botao = document.getElementById('btn-salvar-conta');
  const dados = {
    nome: document.getElementById('conta-nome').value.trim(),
    email: document.getElementById('conta-email').value.trim(),
    senha_atual: document.getElementById('conta-senha-atual').value,
    nova_senha: document.getElementById('conta-nova-senha').value || null,
  };

  botao.disabled = true;
  try {
    const resposta = await apiFetch(window.location.origin + '/auth/me', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dados),
    });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      const detalhe = Array.isArray(corpo.detail)
        ? corpo.detail.map(item => item.msg).join(', ')
        : corpo.detail || 'Não foi possível atualizar a conta.';
      toast(detalhe, 'error');
      return;
    }

    TOKEN = corpo.access_token;
    USUARIO = { ...corpo.usuario, foto: FOTO_TEMP };
    const chaveFoto = `autogestor_foto_${USUARIO.id}`;
    if (FOTO_TEMP) localStorage.setItem(chaveFoto, FOTO_TEMP);
    else localStorage.removeItem(chaveFoto);
    localStorage.setItem('autogestor_token', TOKEN);
    localStorage.setItem('autogestor_usuario', JSON.stringify(USUARIO));
    atualizarPerfilNoHeader();
    fecharMinhaConta();
    toast('Dados da conta atualizados.', 'success');
  } catch (erro) {
    if (erro.message !== 'Sessão expirada') toast('Erro ao conectar com a API.', 'error');
  } finally {
    botao.disabled = false;
  }
}

async function excluirMinhaConta(event) {
  event.preventDefault();
  const botao = document.getElementById('btn-excluir-conta');
  const senhaAtual = document.getElementById('excluir-conta-senha').value;

  botao.disabled = true;
  try {
    const resposta = await apiFetch(window.location.origin + '/auth/me', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ senha_atual: senhaAtual }),
    });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      toast(mensagemHttp(resposta.status, corpo, 'Não foi possível excluir a conta.'), 'error');
      return;
    }

    toast('Conta excluída com sucesso.', 'success');
    fecharExcluirConta();
    setTimeout(() => {
      limparSessaoAutogestor();
      window.location.replace('/static/login.html');
    }, 500);
  } catch (erro) {
    if (erro.message !== 'Sessão expirada') toast('Erro ao conectar com a API.', 'error');
  } finally {
    botao.disabled = false;
  }
}

async function apiFetch(url, options = {}) {
  const { timeoutMs = 12000, ...rest } = options;
  const headers = new Headers(rest.headers || {});
  const token = tokenAtualSessao();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(url, { ...rest, headers, signal: controller.signal });
  } catch (erro) {
    if (erro?.name === 'AbortError') throw new Error('request_timeout');
    throw new Error('network_error');
  } finally {
    clearTimeout(timeoutId);
  }

  if (response.status === 401) {
    let detail = '';
    try {
      const corpo = await response.clone().json();
      if (typeof corpo?.detail === 'string') detail = corpo.detail;
    } catch (_) {}

    if (AUTH_FAILURE_DETAILS.has(detail) || detail === 'Não foi possível validar as credenciais') {
      encerrarSessaoExpirada();
      throw new Error('Sessão expirada');
    }
  }

  return response;
}

async function carregarEspacos() {
  const resposta = await apiFetch(window.location.origin + '/espacos');
  if (!resposta.ok) throw new Error('Não foi possível carregar os espaços.');
  ESPACOS = await resposta.json();
  const salvo = Number(localStorage.getItem(`autogestor_espaco_${USUARIO?.id}`));
  ESPACO_ATUAL = ESPACOS.find(e => e.id === salvo) || ESPACOS.find(e => e.tipo === 'PESSOAL') || ESPACOS[0];
  if (!ESPACO_ATUAL) throw new Error('Nenhum espaço financeiro disponível.');
  atualizarSeletorEspacos();
  definirApiDoEspaco();
}

function definirApiDoEspaco() {
  API = `${window.location.origin}/espacos/${ESPACO_ATUAL.id}/movimentacoes`;
  localStorage.setItem(`autogestor_espaco_${USUARIO?.id}`, String(ESPACO_ATUAL.id));
}

function atualizarSeletorEspacos() {
  document.getElementById('seletor-espaco-nome').textContent = ESPACO_ATUAL?.nome || 'Selecionar espaço';
  const menu = document.getElementById('seletor-espaco-menu');
  menu.replaceChildren(...ESPACOS.map(espaco => {
    const opcao = document.createElement('button');
    opcao.type = 'button';
    opcao.className = `space-picker-option ${espaco.id === ESPACO_ATUAL?.id ? 'active' : ''}`;
    opcao.setAttribute('role', 'option');
    opcao.setAttribute('aria-selected', String(espaco.id === ESPACO_ATUAL?.id));
    const icone = document.createElement('span');
    icone.className = 'space-picker-icon';
    icone.textContent = espaco.tipo === 'PESSOAL' ? '●' : '◆';
    const copia = document.createElement('span');
    copia.className = 'space-picker-copy';
    const nome = document.createElement('span');
    nome.className = 'space-picker-name'; nome.textContent = espaco.nome;
    const meta = document.createElement('span');
    meta.className = 'space-picker-meta';
    meta.textContent = espaco.tipo === 'PESSOAL' ? 'Espaço pessoal' : `Compartilhado · ${espaco.quantidade_membros} membro(s)`;
    copia.append(nome, meta);
    opcao.append(icone, copia);
    if (espaco.id === ESPACO_ATUAL?.id) {
      const check = document.createElement('span');
      check.className = 'space-picker-check'; check.textContent = '✓'; opcao.append(check);
    }
    opcao.addEventListener('click', () => selecionarEspaco(espaco.id));
    return opcao;
  }));
}

function fecharSeletorEspacos() {
  document.getElementById('seletor-espaco-menu').classList.remove('open');
  document.getElementById('seletor-espaco').setAttribute('aria-expanded', 'false');
}

function alternarSeletorEspacos(event) {
  event.stopPropagation();
  fecharMenuPerfil();
  fecharMenuExportacao();
  const menu = document.getElementById('seletor-espaco-menu');
  const aberto = menu.classList.toggle('open');
  document.getElementById('seletor-espaco').setAttribute('aria-expanded', String(aberto));
}

async function selecionarEspaco(id) {
  fecharSeletorEspacos();
  ESPACO_ATUAL = ESPACOS.find(e => e.id === Number(id));
  if (!ESPACO_ATUAL) return;
  definirApiDoEspaco();
  atualizarSeletorEspacos();
  todos = [];
  paginaAtual = 1;
  await carregar();
  toast(`Espaço alterado para ${ESPACO_ATUAL.nome}.`, 'success');
}

function renderizarEspacos() {
  const lista = document.getElementById('lista-espacos');
  document.getElementById('contador-espacos').textContent = ESPACOS.length;
  lista.innerHTML = ESPACOS.map(espaco => `
    <div class="space-item ${espaco.id === ESPACO_ATUAL?.id ? 'current' : ''}">
      <div class="space-item-main">
        <div class="space-item-icon">${espaco.tipo === 'PESSOAL' ? '●' : '◆'}</div>
        <div class="space-item-copy"><div class="space-item-title">${escaparHtml(espaco.nome)}${espaco.id === ESPACO_ATUAL?.id ? '<span class="space-current-badge">ATUAL</span>' : ''}</div><div class="space-item-meta">${espaco.tipo === 'PESSOAL' ? 'Espaço pessoal · somente você' : `Compartilhado · ${espaco.quantidade_membros} de ${espaco.limite_membros} membros · ${espaco.papel}`}</div></div>
      </div>
      <div class="space-item-actions">
        ${espaco.id !== ESPACO_ATUAL?.id ? `<button class="space-mini-button primary" onclick="selecionarEspacoPeloDialogo(${espaco.id})">Selecionar</button>` : ''}
        ${['DONO','ADMIN'].includes(espaco.papel) ? `<button class="space-mini-button" onclick="abrirEdicaoEspaco(${espaco.id})">Editar</button>` : ''}
        ${espaco.codigo_acesso ? `<button class="space-mini-button" onclick="copiarCodigo('${espaco.codigo_acesso}')" title="${espaco.codigo_acesso}">Copiar código</button>` : ''}
        ${espaco.tipo === 'COMPARTILHADO' ? `<button class="space-mini-button" onclick="verMembros(${espaco.id})">Membros</button>` : ''}
        ${espaco.tipo === 'COMPARTILHADO' && ['DONO','ADMIN'].includes(espaco.papel) ? `<button class="space-mini-button danger" onclick="excluirEspaco(${espaco.id})">Excluir</button>` : ''}
      </div>
    </div>`).join('');
}

async function abrirEspacos() {
  fecharSeletorEspacos();
  await carregarEspacos();
  renderizarEspacos();
  fecharMembros();
  document.getElementById('dialog-espacos').showModal();
}

function fecharEspacos() {
  document.getElementById('dialog-espacos').close();
}

function abrirEdicaoEspaco(espacoId) {
  ESPACO_EM_EDICAO = ESPACOS.find(item => item.id === Number(espacoId));
  if (!ESPACO_EM_EDICAO) return;
  fecharEspacos();
  document.getElementById('editar-espaco-nome').value = ESPACO_EM_EDICAO.nome;
  document.getElementById('editar-espaco-tipo').textContent = ESPACO_EM_EDICAO.tipo === 'PESSOAL' ? 'Espaço pessoal' : 'Espaço compartilhado';
  const codigoWrap = document.getElementById('editar-codigo-wrap');
  codigoWrap.style.display = ESPACO_EM_EDICAO.tipo === 'COMPARTILHADO' ? 'flex' : 'none';
  document.getElementById('editar-limite-wrap').style.display = ESPACO_EM_EDICAO.tipo === 'COMPARTILHADO' ? 'block' : 'none';
  document.getElementById('editar-espaco-limite').value = ESPACO_EM_EDICAO.limite_membros;
  document.getElementById('editar-codigo-ativo').checked = Boolean(ESPACO_EM_EDICAO.codigo_ativo);
  document.getElementById('dialog-editar-espaco').showModal();
  setTimeout(() => document.getElementById('editar-espaco-nome').focus(), 80);
}

function fecharEdicaoEspaco() {
  document.getElementById('dialog-editar-espaco').close();
  ESPACO_EM_EDICAO = null;
  abrirEspacos();
}

async function salvarEdicaoEspaco(event) {
  event.preventDefault();
  if (!ESPACO_EM_EDICAO) return;
  const botao = document.getElementById('btn-salvar-espaco');
  const dados = { nome: document.getElementById('editar-espaco-nome').value.trim() };
  if (ESPACO_EM_EDICAO.tipo === 'COMPARTILHADO') {
    dados.codigo_ativo = document.getElementById('editar-codigo-ativo').checked;
    dados.limite_membros = Number(document.getElementById('editar-espaco-limite').value);
  }
  botao.disabled = true;
  try {
    const resposta = await apiFetch(`${window.location.origin}/espacos/${ESPACO_EM_EDICAO.id}`, {
      method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify(dados),
    });
    const corpo = await resposta.json();
    if (!resposta.ok) return toast(corpo.detail || 'Não foi possível atualizar o espaço.', 'error');
    document.getElementById('dialog-editar-espaco').close();
    await carregarEspacos();
    renderizarEspacos();
    ESPACO_EM_EDICAO = null;
    document.getElementById('dialog-espacos').showModal();
    toast('Espaço atualizado com sucesso.', 'success');
  } finally {
    botao.disabled = false;
  }
}

async function selecionarEspacoPeloDialogo(id) {
  await selecionarEspaco(id);
  document.getElementById('dialog-espacos').close();
}

async function criarEspaco() {
  const nome = document.getElementById('novo-espaco-nome').value.trim();
  const limite_membros = Number(document.getElementById('novo-espaco-limite').value);
  if (nome.length < 2) return toast('Informe um nome para o espaço.', 'error');
  if (limite_membros < 2 || limite_membros > 20) return toast('O limite deve ficar entre 2 e 20 membros.', 'error');
  const resposta = await apiFetch(window.location.origin + '/espacos/compartilhados', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({nome, limite_membros}) });
  const corpo = await resposta.json();
  if (!resposta.ok) return toast(corpo.detail || 'Não foi possível criar o espaço.', 'error');
  document.getElementById('novo-espaco-nome').value = '';
  await carregarEspacos(); renderizarEspacos(); toast('Espaço compartilhado criado.', 'success');
}

async function entrarEspaco() {
  const codigo = document.getElementById('codigo-espaco').value.trim().toUpperCase();
  const resposta = await apiFetch(window.location.origin + '/espacos/entrar', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({codigo}) });
  const corpo = await resposta.json();
  if (!resposta.ok) return toast(corpo.detail || 'Não foi possível entrar no espaço.', 'error');
  document.getElementById('codigo-espaco').value = '';
  await carregarEspacos(); renderizarEspacos(); toast('Você entrou no espaço.', 'success');
}

async function copiarCodigo(codigo) {
  await navigator.clipboard.writeText(codigo);
  toast(`Código ${codigo} copiado.`, 'success');
}

async function verMembros(espacoId) {
  const resposta = await apiFetch(`${window.location.origin}/espacos/${espacoId}/membros`);
  const membros = await resposta.json();
  if (!resposta.ok) return toast(membros.detail || 'Não foi possível listar os membros.', 'error');
  const espaco = ESPACOS.find(item => item.id === Number(espacoId));
  document.getElementById('titulo-membros').textContent = `Membros · ${espaco?.nome || 'Espaço'}`;
  const lista = document.getElementById('lista-membros');
  lista.replaceChildren(...membros.map(membro => {
    const item = document.createElement('div');
    item.className = 'space-member';
    const avatar = document.createElement('div');
    avatar.className = 'space-member-avatar';
    avatar.textContent = iniciaisDoNome(membro.nome).toUpperCase();
    const copia = document.createElement('div');
    const nome = document.createElement('div');
    nome.className = 'space-member-name'; nome.textContent = membro.nome;
    const email = document.createElement('div');
    email.className = 'space-member-email'; email.textContent = membro.email;
    copia.append(nome, email);
    const papel = document.createElement('div');
    papel.className = 'space-member-role'; papel.textContent = membro.papel;
    item.append(avatar, copia, papel);
    return item;
  }));
  document.getElementById('painel-membros').classList.add('open');
}

function fecharMembros() {
  document.getElementById('painel-membros').classList.remove('open');
}

async function excluirEspaco(espacoId) {
  const espaco = ESPACOS.find(item => item.id === Number(espacoId));
  if (!espaco) return;
  const confirmado = window.confirm(
    `Excluir o espaço "${espaco.nome}"?\n\nTodas as movimentações e vínculos de membros desse espaço serão apagados. Esta ação não pode ser desfeita.`
  );
  if (!confirmado) return;

  const resposta = await apiFetch(`${window.location.origin}/espacos/${espacoId}`, { method: 'DELETE' });
  if (!resposta.ok) {
    let detalhe = 'Não foi possível excluir o espaço.';
    try { detalhe = (await resposta.json()).detail || detalhe; } catch (_) {}
    return toast(detalhe, 'error');
  }

  const excluiuAtual = ESPACO_ATUAL?.id === Number(espacoId);
  await carregarEspacos();
  renderizarEspacos();
  if (excluiuAtual) await carregar();
  toast('Espaço excluído com sucesso.', 'success');
}

async function inicializarAplicacao() {
  try {
    await carregarEspacos();
    await carregar();
  } catch (erro) {
    revelarUI();
    document.getElementById('load-error').hidden = false;
    ['saldo-ganhos', 'saldo-gastos', 'saldo-liquido'].forEach(id => document.getElementById(id).textContent = '—');
    toast(erro.message || 'Não foi possível iniciar o aplicativo.', 'error');
  }
}

function escaparHtml(valor) {
  return String(valor ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

let todos = [];
let filtroAtivo = 'TODOS';
let tipoAtivo = 'GANHO';

// ── ESTADO DO FILTRO DE PERÍODO ──────────────────────────────
// periodoAtivo guarda qual pill está selecionada: 'tudo' | 'hoje' | '7d' | 'mes' | 'custom'
let periodoAtivo = 'tudo';
// Quando periodoAtivo === 'custom', estas duas guardam o intervalo escolhido
let periodoInicio = null;
let periodoFim = null;

// ── ESTADO DE ORDENAÇÃO ──────────────────────────────────────
// 'recente' | 'antigo' | 'maior' | 'menor'
let ordenacaoAtiva = 'recente';

// ── ESTADO DE PAGINAÇÃO ──────────────────────────────────────
let paginaAtual = 1;
let listaCompleta = false;
const ITENS_POR_PAGINA = 5; // ajustável: quantos itens aparecem por página

function fmt(v) {
  return 'R$ ' + Math.abs(v).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
function fmtData(d) {
  if (!d) return '';
  const [y, m, dia] = d.split('-');
  return `${dia}/${m}/${y}`;
}

/*
  revelarUI()
  ───────────
  Chamada uma única vez quando a API responde com sucesso.
  Remove todos os skeletons e exibe os elementos reais.

  A troca é feita alterando display:
    skeleton  → display: none   (some)
    real      → display: flex/grid/block  (aparece)

  Não usamos opacity ou visibility porque o skeleton
  ainda ocupa espaço no layout se não for removido de vez.
*/
function revelarUI() {
  // Esconde skeletons
  document.getElementById('sk-saldo').style.display   = 'none';
  document.getElementById('sk-lista').style.display   = 'none';
  document.getElementById('sk-sidebar').style.display = 'none';

  // Mostra conteúdo real
  document.getElementById('real-saldo').style.display   = 'grid';
  document.getElementById('real-sidebar').style.display = 'flex';
  document.getElementById('lista').style.display        = 'block';
}

function setTipo(tipo) {
  tipoAtivo = tipo;
  document.getElementById('btn-ganho').classList.toggle('active', tipo === 'GANHO');
  document.getElementById('btn-gasto').classList.toggle('active', tipo === 'GASTO');
  const btn = document.getElementById('btn-salvar');
  btn.className = `btn-primary ${tipo === 'GANHO' ? 'ganho' : 'gasto'}`;
  btn.textContent = tipo === 'GANHO' ? 'Registrar ganho' : 'Registrar gasto';
}

function setFiltro(filtro, el) {
  filtroAtivo = filtro;
  document.querySelectorAll('#filtros .filter-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  paginaAtual = 1; // volta pra primeira página ao trocar de filtro
  atualizarTudo();
}

/*
  setPeriodo(chave, el)
  ─────────────────────
  Chamada ao clicar em qualquer pill de período (Hoje, 7 dias, etc).

  Caso especial: 'custom' não filtra imediatamente — só revela
  os dois campos de data. O filtro real só é aplicado quando o
  usuário clica em "Aplicar" (função aplicarPeriodoCustom).
  Isso evita filtrar com datas incompletas enquanto o usuário
  ainda está escolhendo o intervalo.
*/
function setPeriodo(chave, el) {
  document.querySelectorAll('#filtros-periodo .filter-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');

  const customBox = document.getElementById('custom-range');

  if (chave === 'custom') {
    // Apenas mostra os campos — não filtra ainda
    customBox.classList.add('show');
    return;
  }

  // Qualquer outra opção esconde o intervalo customizado
  customBox.classList.remove('show');
  periodoAtivo = chave;
  paginaAtual = 1; // volta pra primeira página ao trocar de período

  /*
    DEBUG: abra o Console do navegador (F12 → aba Console) e
    clique em "Hoje". Mostra a data calculada como "hoje" e
    as datas reais das movimentações, para comparar formatos.
  */
  if (chave === 'hoje') {
    console.log('🔍 Debug filtro Hoje — data calculada:', dataLocalISO(new Date()));
    console.log('🔍 Datas das movimentações no sistema:', todos.map(m => m.data));
  }

  atualizarTudo();
}

/*
  aplicarPeriodoCustom()
  ───────────────────────
  Lê os dois campos de data, valida, e aplica o filtro customizado.
*/
function aplicarPeriodoCustom() {
  const inicio = document.getElementById('data-inicio').value;
  const fim    = document.getElementById('data-fim').value;

  if (!inicio || !fim) {
    if (!inicio) document.getElementById('data-inicio').focus();
    else document.getElementById('data-fim').focus();
    return;
  }

  if (inicio > fim) {
    toast('A data inicial não pode ser maior que a data final.', 'error');
    document.getElementById('data-inicio').focus();
    return;
  }

  periodoAtivo  = 'custom';
  periodoInicio = inicio;
  periodoFim    = fim;
  paginaAtual = 1; // volta pra primeira página ao aplicar período customizado
  atualizarTudo();
}

/*
  dataLocalISO(date)
  ────────────────────
  BUG CORRIGIDO: toISOString() sempre converte para UTC.
  Se você está no Brasil (UTC-3) e são, por exemplo, 22h,
  toISOString() já devolve a data de AMANHÃ em UTC.
  Resultado: o filtro "Hoje" nunca batia com a data salva
  no banco (que é a data local, sem fuso).

  Esta função monta a string 'YYYY-MM-DD' usando os componentes
  LOCAIS da data (getFullYear/getMonth/getDate), que respeitam
  o fuso horário do navegador do usuário — exatamente o que
  o <input type="date"> também usa internamente.
*/
function dataLocalISO(date) {
  const ano = date.getFullYear();
  const mes = String(date.getMonth() + 1).padStart(2, '0'); // getMonth() é 0-indexado
  const dia = String(date.getDate()).padStart(2, '0');
  return `${ano}-${mes}-${dia}`;
}

/*
  dentroDoPeriodo(dataStr)
  ─────────────────────────
  Recebe a data de uma movimentação (string 'YYYY-MM-DD') e
  retorna true/false se ela cai dentro do período selecionado.

  Comparamos strings de data ISO diretamente (sem criar Date)
  sempre que possível, pois 'YYYY-MM-DD' é comparável léxicamente
  na mesma ordem que cronologicamente — evita bugs de timezone.
*/
function dentroDoPeriodo(dataStr) {
  if (periodoAtivo === 'tudo') return true;
  if (!dataStr) return false;

  /*
    CORREÇÃO ADICIONAL:
    A API (FastAPI/Pydantic) pode serializar um campo `date` como
    "2026-06-29" OU como "2026-06-29T00:00:00" dependendo do banco
    e da versão do driver. Se vier com timestamp, a comparação de
    string direta ("2026-06-29T00:00:00" === "2026-06-29") falha
    silenciosamente e o filtro "Hoje" nunca bate.

    slice(0, 10) garante que pegamos só "YYYY-MM-DD" não importa
    o que vier depois.
  */
  dataStr = String(dataStr).slice(0, 10);

  const hoje = new Date();
  const hojeISO = dataLocalISO(hoje);   // usa data local, não UTC

  if (periodoAtivo === 'hoje') {
    return dataStr === hojeISO;
  }

  if (periodoAtivo === '7d') {
    const limite = new Date(hoje);
    limite.setDate(limite.getDate() - 7);
    const limiteISO = dataLocalISO(limite);
    return dataStr >= limiteISO && dataStr <= hojeISO;
  }

  if (periodoAtivo === 'mes') {
    const mesAtual = hojeISO.slice(0, 7);
    return dataStr.slice(0, 7) === mesAtual;
  }

  if (periodoAtivo === 'custom') {
    return dataStr >= periodoInicio && dataStr <= periodoFim;
  }

  return true;
}

/*
  atualizarTudo()
  ────────────────
  Função central chamada sempre que QUALQUER filtro muda
  (tipo ou período). Re-renderiza tudo que depende dos dados
  filtrados: lista, stats, saldo e gráfico.

  Centralizar aqui evita esquecer de atualizar algum painel
  quando um novo filtro é adicionado no futuro.
*/
function atualizarTudo() {
  renderLista();
  renderStats();
  renderSaldo();
  renderChart();
  renderEvolucao();
  renderMetas();
}

/*
  getDadosFiltrados()
  ────────────────────
  Aplica AMBOS os filtros (tipo + período) de uma vez.
  Todas as funções de render usam esta função como fonte única
  de dados — assim tipo e período sempre trabalham em conjunto,
  nunca um anulando o outro.
*/
function getDadosFiltrados() {
  return todos
    .filter(m => filtroAtivo === 'TODOS' || m.tipo === filtroAtivo)
    .filter(m => dentroDoPeriodo(m.data));
}

function normalizarMovimentacao(item) {
  return {
    ...item,
    valor: Number.parseFloat(item?.valor ?? 0) || 0,
  };
}

function inserirMovimentacaoLocal(item) {
  const normalizada = normalizarMovimentacao(item);
  const indice = todos.findIndex(m => Number(m.id) === Number(normalizada.id));
  if (indice >= 0) {
    todos[indice] = normalizada;
  } else {
    todos = [normalizada, ...todos];
  }
}

function removerMovimentacaoLocal(id) {
  todos = todos.filter(m => Number(m.id) !== Number(id));
}

/* ════════════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
   ════════════════════════════════════════════════════════════
   Substitui window.alert() por uma notificação não-bloqueante.
   Uso: toast('Mensagem', 'success' | 'error' | 'info')
──────────────────────────────────────────────────────────── */

const TOAST_ICONS = { success: '✓', error: '✕', info: 'ℹ' };

/*
  toast(mensagem, tipo, duracaoMs)
  ───────────────────────────────────
  Cria o elemento do toast, injeta no container, e agenda
  sua remoção automática após `duracaoMs` (padrão 3.5s).

  O usuário também pode fechar manualmente clicando no X —
  nesse caso, cancelamos o timer automático para não tentar
  remover um elemento que já foi removido.
*/
function toast(mensagem, tipo = 'info', duracaoMs = 3500) {
  const container = document.getElementById('toast-container');

  const el = document.createElement('div');
  el.className = `toast ${tipo}`;
  const icon = document.createElement('span');
  icon.className = 'toast-icon';
  icon.textContent = TOAST_ICONS[tipo] || 'ℹ';
  const texto = document.createElement('span');
  texto.className = 'toast-text';
  texto.textContent = mensagem;
  const fechar = document.createElement('button');
  fechar.className = 'toast-close';
  fechar.title = 'Fechar';
  fechar.textContent = '×';
  el.append(icon, texto, fechar);
  container.appendChild(el);

  // Função que anima a saída e remove o elemento do DOM
  function remover() {
    el.classList.add('toast-out');
    // Espera a animação de saída (0.2s) terminar antes de
    // remover de fato — senão o toast "pula" sem a animação.
    setTimeout(() => el.remove(), 200);
  }

  // Fechar manualmente pelo botão X
  el.querySelector('.toast-close').addEventListener('click', remover);

  // Remoção automática após o tempo definido
  const timer = setTimeout(remover, duracaoMs);

  // Se o usuário fechar manualmente, cancela o timer automático
  // para não chamar remover() duas vezes
  el.querySelector('.toast-close').addEventListener('click', () => clearTimeout(timer));
}

/* ════════════════════════════════════════════════════════════
   GRÁFICO DE EVOLUÇÃO DO SALDO
   ════════════════════════════════════════════════════════════
   Desenha um SVG de linha mostrando o saldo acumulado dia a dia,
   dentro do período/filtro ativo. Sem biblioteca externa de
   gráficos — controle total sobre o visual.
──────────────────────────────────────────────────────────── */

/*
  renderEvolucao()
  ──────────────────
  1. Pega os dados filtrados (mesmo filtro de tipo+período da tela)
  2. Agrupa por data e calcula o saldo do dia (ganhos - gastos)
  3. Ordena por data e calcula o saldo ACUMULADO até cada dia
  4. Converte os pontos em coordenadas SVG e desenha a linha
*/
function renderEvolucao() {
  const wrap = document.getElementById('evolucao-wrap');
  const dados = todos.filter(m => dentroDoPeriodo(m.data));
  if (!dados.length) {
    wrap.innerHTML = '<div class="chart-empty">Seu resultado começa aqui.<span>Registre uma entrada ou saída para acompanhar a evolução.</span></div>';
    return;
  }
  const porDia = {};
  dados.forEach(m => {
    const dia = String(m.data).slice(0, 10);
    porDia[dia] = (porDia[dia] || 0) + (m.tipo === 'GANHO' ? m.valor : -m.valor);
  });
  let acumulado = 0;
  const pontos = Object.keys(porDia).sort().map(data => ({ data, saldo: acumulado += porDia[data] }));
  const largura = Math.max(240, wrap.clientWidth);
  const altura = 210;
  const margem = { esquerda: 58, direita: 14, topo: 20, base: 34 };
  const larguraUtil = largura - margem.esquerda - margem.direita;
  const alturaUtil = altura - margem.topo - margem.base;
  const max = Math.max(1, ...pontos.map(p => p.saldo));
  const min = Math.min(0, ...pontos.map(p => p.saldo));
  const amplitude = max - min || 1;
  const dataNumero = data => Date.parse(data + 'T00:00:00Z');
  const inicio = dataNumero(pontos[0].data);
  const intervalo = dataNumero(pontos[pontos.length - 1].data) - inicio;
  const x = p => margem.esquerda + (intervalo ? (dataNumero(p.data) - inicio) / intervalo : .5) * larguraUtil;
  const y = valor => margem.topo + (max - valor) / amplitude * alturaUtil;
  const moeda = valor => valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const eixo = valor => valor.toLocaleString('pt-BR', { notation:'compact', maximumFractionDigits:1 });
  const linha = pontos.map(p => `${x(p)},${y(p.saldo)}`).join(' ');
  const grades = [max, min + amplitude / 2, min].map(valor => `<g><line x1="${margem.esquerda}" y1="${y(valor)}" x2="${largura - margem.direita}" y2="${y(valor)}" stroke="var(--border)" stroke-dasharray="3 5"/><text x="${margem.esquerda - 10}" y="${y(valor) + 4}" text-anchor="end" fill="var(--muted)" font-size="10">${eixo(valor)}</text></g>`).join('');
  const indices = [...new Set(largura < 380 ? [0, pontos.length - 1] : [0, Math.floor((pontos.length - 1) / 2), pontos.length - 1])];
  const datas = indices.map(i => `<text x="${x(pontos[i])}" y="${altura - 7}" text-anchor="${i === 0 ? 'start' : i === pontos.length - 1 ? 'end' : 'middle'}" fill="var(--muted)" font-size="10">${fmtData(pontos[i].data).slice(0,5)}</text>`).join('');
  wrap.innerHTML = `<div class="chart-unit">RESULTADO ACUMULADO · R$</div>
    <svg role="img" aria-label="Resultado acumulado por data, em reais" class="evolucao-svg-wrap" viewBox="0 0 ${largura} ${altura}" style="width:100%;height:${altura}px">
      ${grades}
      <polyline points="${linha}" fill="none" stroke="var(--accent2)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
      ${pontos.map((p, i) => `<circle cx="${x(p)}" cy="${y(p.saldo)}" r="3.5" fill="var(--accent2)"/><circle class="evo-hover-point" tabindex="0" role="button" aria-label="${fmtData(p.data)}: ${moeda(p.saldo)}" cx="${x(p)}" cy="${y(p.saldo)}" r="12" fill="transparent" data-index="${i}"/>`).join('')}
      ${datas}
    </svg><div class="chart-reading" aria-live="polite"></div>`;
  const leitura = wrap.querySelector('.chart-reading');
  const mostrar = ponto => { leitura.textContent = `${fmtData(ponto.data)} · ${moeda(ponto.saldo)}`; };
  mostrar(pontos[pontos.length - 1]);
  wrap.querySelectorAll('.evo-hover-point').forEach(el => {
    ['mouseenter', 'focus', 'click'].forEach(evento => el.addEventListener(evento, () => mostrar(pontos[Number(el.dataset.index)])));
    el.addEventListener('keydown', evento => { if (evento.key === 'Enter' || evento.key === ' ') { evento.preventDefault(); mostrar(pontos[Number(el.dataset.index)]); } });
  });
}

/* ════════════════════════════════════════════════════════════
   METAS DE GASTO POR CATEGORIA
   ════════════════════════════════════════════════════════════
   Persistência via localStorage (chave 'autogestor_metas').

   ESTRUTURA SALVA: array de objetos { categoria, limite }
   Exemplo: [{ categoria: "Combustível", limite: 500 }]

   NOTA IMPORTANTE (ver explicação completa no chat):
   Isso funciona perfeitamente para uso pessoal num navegador,
   mas não sincroniza entre dispositivos nem aparece se você
   limpar os dados do navegador. Se quiser persistir de verdade,
   precisa de um endpoint novo na API (ver sugestão no final).
──────────────────────────────────────────────────────────── */

const METAS_STORAGE_KEY = 'autogestor_metas';

function carregarMetas() {
  try {
    const raw = localStorage.getItem(METAS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function salvarMetas(metas) {
  localStorage.setItem(METAS_STORAGE_KEY, JSON.stringify(metas));
}

/*
  adicionarMeta()
  ─────────────────
  Lê os campos do formulário no fim do card de metas,
  valida, adiciona ao array e re-renderiza.
*/
function adicionarMeta() {
  const categoria = document.getElementById('meta-categoria').value.trim();
  const limite = parseFloat(document.getElementById('meta-valor').value);

  if (!categoria || !limite || limite <= 0) {
    toast('Preencha categoria e valor da meta.', 'error');
    return;
  }

  const metas = carregarMetas();

  // Se já existe uma meta para essa categoria, atualiza em vez de duplicar
  const existente = metas.find(m => m.categoria.toLowerCase() === categoria.toLowerCase());
  if (existente) {
    existente.limite = limite;
    toast(`Meta de "${categoria}" atualizada.`, 'success');
  } else {
    metas.push({ categoria, limite });
    toast(`Meta de "${categoria}" criada.`, 'success');
  }

  salvarMetas(metas);

  document.getElementById('meta-categoria').value = '';
  document.getElementById('meta-valor').value = '';

  renderMetas();
}

function removerMeta(categoria) {
  let metas = carregarMetas();
  metas = metas.filter(m => m.categoria !== categoria);
  salvarMetas(metas);
  renderMetas();
  toast(`Meta de "${categoria}" removida.`, 'info');
}

/*
  renderMetas()
  ───────────────
  Para cada meta cadastrada, calcula quanto já foi gasto NESSE
  MÊS na categoria correspondente (sempre mês atual, independente
  do filtro de período da tela — meta é sempre mensal por definição)
  e desenha a barra de progresso.

  Cores da barra:
    < 80%   → verde   (ok)
    80-99%  → âmbar   (atenção)
    >= 100% → vermelho (estourou)
*/
function renderMetas() {
  const lista = document.getElementById('metas-lista');
  const metas = carregarMetas();

  if (!metas.length) {
    lista.innerHTML = '<div class="meta-empty">Nenhuma meta cadastrada ainda</div>';
    return;
  }

  // Gastos do mês atual, agrupados por categoria
  const hojeISO = dataLocalISO(new Date());
  const mesAtual = hojeISO.slice(0, 7);

  const gastosDoMes = {};
  todos
    .filter(m => m.tipo === 'GASTO' && String(m.data).slice(0, 7) === mesAtual)
    .forEach(m => {
      gastosDoMes[m.categoria] = (gastosDoMes[m.categoria] || 0) + m.valor;
    });

  lista.innerHTML = metas.map(meta => {
    const gasto = gastosDoMes[meta.categoria] || 0;
    const pct = Math.min(Math.round((gasto / meta.limite) * 100), 999); // cap visual em 999%

    let statusClasse = 'ok';
    if (pct >= 100) statusClasse = 'estourou';
    else if (pct >= 80) statusClasse = 'atencao';

    // Largura da barra nunca passa de 100% visualmente, mesmo
    // que o gasto real ultrapasse a meta (senão a barra "vaza" do card)
    const larguraBarra = Math.min(pct, 100);

    return `
      <div class="meta-item">
        <div class="meta-header">
          <span class="meta-nome">${meta.categoria}
            <button class="meta-delete" onclick="removerMeta('${meta.categoria.replace(/'/g, "\\'")}')">remover</button>
          </span>
          <span class="meta-valores">${fmt(gasto)} / ${fmt(meta.limite)}</span>
        </div>
        <div class="meta-bar-bg">
          <div class="meta-bar-fill ${statusClasse}" style="width:${larguraBarra}%"></div>
        </div>
        <div class="meta-pct-label ${statusClasse}">
          ${pct}% ${statusClasse === 'estourou' ? '— meta estourada' : statusClasse === 'atencao' ? '— atenção' : ''}
        </div>
      </div>
    `;
  }).join('');
}

/* ════════════════════════════════════════════════════════════
   EXPORTAÇÃO: CSV e Excel
   ════════════════════════════════════════════════════════════

   AMBAS as funções partem da mesma base: montarLinhasExport().
   Isso garante que CSV e Excel sempre tenham exatamente as
   mesmas colunas e os mesmos dados — só muda o formato do
   arquivo final.

   IMPORTANTE: usamos getDadosFiltrados(), não 'todos' direto.
   Ou seja, o usuário exporta exatamente o que está vendo na
   tela (com os filtros de tipo e período aplicados). Isso é
   o comportamento esperado em qualquer ferramenta financeira
   real — exportar "tudo" quando só "Mês atual" está selecionado
   seria confuso e até gerar relatórios incorretos.
──────────────────────────────────────────────────────────── */

/*
  montarLinhasExport()
  ──────────────────────
  Transforma os dados brutos da API (campos em inglês/técnico,
  tipo 'GANHO'/'GASTO', data 'YYYY-MM-DD') em um array de objetos
  com cabeçalhos legíveis em português — prontos para virar
  planilha. Também ordena por data, mais recente primeiro.
*/
function montarLinhasExport() {
  const dados = [...getDadosFiltrados()].sort((a, b) => new Date(b.data) - new Date(a.data));

  return dados.map(m => ({
    'Data':        fmtData(m.data),
    'Tipo':        m.tipo === 'GANHO' ? 'Ganho' : 'Gasto',
    'Categoria':   m.categoria,
    'Descrição':   m.descricao || '',
    // Valor numérico puro (sem "R$") para que o Excel reconheça
    // a coluna como número e permita somas/fórmulas direto na planilha.
    // Gastos saem negativos para que o somatório da coluna já
    // dê o saldo líquido automaticamente.
    'Valor (R$)':  m.tipo === 'GASTO' ? -m.valor : m.valor,
  }));
}

/*
  nomeArquivoExport(extensao)
  ─────────────────────────────
  Gera um nome de arquivo com a data atual embutida, ex:
  "autogestor_movimentacoes_2026-06-29.csv"
  Isso evita que o usuário acumule vários arquivos chamados
  "export.csv" e perca o controle de qual é o mais recente.
*/
function nomeArquivoExport(extensao) {
  const hojeISO = dataLocalISO(new Date());
  return `autogestor_movimentacoes_${hojeISO}.${extensao}`;
}

/*
  exportarCSV()
  ──────────────
  Gera um CSV puro, sem depender da biblioteca SheetJS — CSV é
  só texto, então construímos a string manualmente. Isso também
  serve como exemplo de como funciona um CSV "por baixo do capô"
  (separador, escaping de aspas, etc).
*/
function exportarCSV() {
  const linhas = montarLinhasExport();

  if (!linhas.length) {
    toast('Não há movimentações para exportar com os filtros atuais.', 'error');
    return;
  }

  const colunas = Object.keys(linhas[0]);

  /*
    Escapar campos com vírgula, aspas ou quebra de linha:
    regra do formato CSV (RFC 4180) — se o campo contém vírgula,
    aspas ou \n, ele precisa ser envolvido em aspas duplas, e
    qualquer aspas dupla interna vira duas aspas duplas ("").
  */
  function escapeCSV(valor) {
    const str = String(valor);
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
  }

  const linhaCabecalho = colunas.map(escapeCSV).join(',');
  const linhasDados = linhas.map(linha =>
    colunas.map(col => escapeCSV(linha[col])).join(',')
  );

  // \uFEFF (BOM) no início garante que o Excel abra o CSV
  // reconhecendo corretamente os acentos (UTF-8 com BOM).
  // Sem isso, "Descrição" pode virar "DescriÃ§Ã£o" no Excel.
  const csvContent = '\uFEFF' + [linhaCabecalho, ...linhasDados].join('\r\n');

  baixarArquivo(csvContent, nomeArquivoExport('csv'), 'text/csv;charset=utf-8;');
  toast('CSV exportado com sucesso.', 'success');
}

/*
  exportarExcel()
  ────────────────
  Usa a biblioteca SheetJS (window.XLSX) para gerar um arquivo
  .xlsx de verdade — com tipos de dados nativos (números reais,
  não texto), múltiplas linhas, e compatível com Excel/Google Sheets
  sem precisar de nenhuma conversão.
*/
function exportarExcel() {
  const linhas = montarLinhasExport();

  if (!linhas.length) {
    toast('Não há movimentações para exportar com os filtros atuais.', 'error');
    return;
  }

  // json_to_sheet converte o array de objetos JS direto em
  // uma planilha, usando as chaves do objeto como cabeçalho.
  const planilha = XLSX.utils.json_to_sheet(linhas);

  // Define larguras de coluna manualmente para o arquivo já
  // abrir legível, sem o usuário precisar redimensionar nada.
  planilha['!cols'] = [
    { wch: 12 },  // Data
    { wch: 10 },  // Tipo
    { wch: 18 },  // Categoria
    { wch: 30 },  // Descrição
    { wch: 14 },  // Valor (R$)
  ];

  // Um "workbook" pode ter várias abas — aqui criamos uma só,
  // nomeada "Movimentações".
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, planilha, 'Movimentações');

  // writeFile já cuida de gerar o blob e disparar o download
  // do navegador — não precisamos da função baixarArquivo aqui.
  XLSX.writeFile(workbook, nomeArquivoExport('xlsx'));
  toast('Excel exportado com sucesso.', 'success');
}

/*
  baixarArquivo(conteudo, nomeArquivo, mimeType)
  ─────────────────────────────────────────────────
  Função utilitária usada pelo CSV (o Excel já tem seu próprio
  mecanismo de download via XLSX.writeFile).

  Cria um Blob (arquivo em memória), gera uma URL temporária
  para ele, simula um clique num link <a> invisível para disparar
  o download, e depois limpa tudo da memória.
*/
function baixarArquivo(conteudo, nomeArquivo, mimeType) {
  const blob = new Blob([conteudo], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Libera a memória usada pela URL temporária
  URL.revokeObjectURL(url);
}

async function salvar() {
  const categoria = document.getElementById('categoria').value.trim();
  const descricao = document.getElementById('descricao').value.trim() || null;
  const valor = parseFloat(document.getElementById('valor').value);
  const data = document.getElementById('data').value;

  if (!categoria || !valor || valor <= 0 || !data) {
    if (!categoria) document.getElementById('categoria').focus();
    else if (!data) document.getElementById('data').focus();
    else document.getElementById('valor').focus();
    return;
  }

  try {
    const res = await apiFetch(API + '/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tipo: tipoAtivo, categoria, descricao, valor, data })
    });

    /*
      CORREÇÃO IMPORTANTE:
      fetch() só lança erro (cai no catch) se houver falha de REDE
      (servidor offline, sem internet, CORS bloqueado, etc).
      Se o servidor responder com erro HTTP (400, 422, 500...),
      o fetch considera "sucesso" mesmo assim — só o status muda.

      Sem essa checagem, um erro de validação do Pydantic (422)
      passava batido: o formulário limpava, aparecia "sucesso",
      mas nada era salvo no banco. Por isso parecia que "nenhum
      parâmetro atualiza" — na real a requisição estava falhando
      silenciosamente.
    */
    if (!res.ok) {
      let detalhe = `Erro ${res.status}`;
      try {
        const corpo = await res.json();
        // FastAPI/Pydantic geralmente retorna o erro em `detail`
        if (corpo.detail) {
          detalhe = Array.isArray(corpo.detail)
            ? corpo.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
            : corpo.detail;
        }
      } catch (_) { /* corpo não era JSON, mantém a mensagem genérica */ }

      toast(`Falha ao salvar: ${detalhe}`, 'error');
      console.error('Erro ao salvar movimentação:', detalhe);
      return; // não limpa o formulário nem recarrega — usuário pode corrigir e tentar de novo
    }

    const criada = normalizarMovimentacao(await res.json());
    document.getElementById('categoria').value = '';
    document.getElementById('descricao').value = '';
    document.getElementById('valor').value = '';
    inserirMovimentacaoLocal(criada);
    atualizarTudo();
    toast(`${tipoAtivo === 'GANHO' ? 'Ganho' : 'Gasto'} registrado com sucesso.`, 'success');
  } catch(e) {
    // Este catch agora só pega erros REAIS de rede/conexão
    toast('Erro ao conectar com a API. Verifique se o servidor está rodando.', 'error');
    console.error('Erro de rede ao salvar:', e);
  }
}

async function carregar() {
  document.getElementById("load-error").hidden = true;
  /*
    Na primeira chamada (page load), o skeleton já está visível no HTML.
    Nas chamadas seguintes (após salvar/deletar), a UI real já foi revelada,
    então não precisamos re-exibir o skeleton — apenas atualizamos os dados.
  */
  try {
    const res = await apiFetch(API + '/');
    if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
    todos = await res.json();
    if (!Array.isArray(todos)) throw new Error('Resposta inválida da API');
    todos = todos.map(normalizarMovimentacao);

    // Revela a UI real e esconde os skeletons (só tem efeito na 1ª chamada;
    // nas chamadas seguintes os elementos já estão no estado correto)
    revelarUI();

    atualizarTudo();
  } catch(e) {
    revelarUI();
    document.getElementById('load-error').hidden = false;
    if (!todos.length) {
      ['saldo-ganhos', 'saldo-gastos', 'saldo-liquido'].forEach(id => document.getElementById(id).textContent = '—');
      document.getElementById('lista').innerHTML = '<div class="empty"><div class="empty-text">Seus dados ainda não foram carregados. Tente novamente.</div></div>';
    }
  }
}

function renderSaldo() {
  // Indicadores refletem o período; filtros da lista não alteram o resultado financeiro.
  const dados = todos.filter(m => dentroDoPeriodo(m.data));
  const ganhos = dados.filter(m => m.tipo === 'GANHO').reduce((s, m) => s + m.valor, 0);
  const gastos = dados.filter(m => m.tipo === 'GASTO').reduce((s, m) => s + m.valor, 0);
  const liquido = ganhos - gastos;

  document.getElementById('saldo-ganhos').textContent = fmt(ganhos);
  document.getElementById('saldo-gastos').textContent = fmt(gastos);

  const el = document.getElementById('saldo-liquido');
  el.textContent = (liquido < 0 ? '- ' : '') + fmt(liquido);
  el.className = 'saldo-value ' + (liquido >= 0 ? 'positive' : 'negative');
}

function renderStats() {
  const dados = todos.filter(m => dentroDoPeriodo(m.data));
  const ganhos = dados.filter(m => m.tipo === 'GANHO');
  const gastos = dados.filter(m => m.tipo === 'GASTO');
  const totalG  = ganhos.reduce((s, m) => s + m.valor, 0);
  const totalGa = gastos.reduce((s, m) => s + m.valor, 0);

  document.getElementById('total-ganhos').textContent = fmt(totalG);
  document.getElementById('qtd-ganhos').textContent   = ganhos.length + ' lançamento' + (ganhos.length !== 1 ? 's' : '');
  document.getElementById('total-gastos').textContent = fmt(totalGa);
  document.getElementById('qtd-gastos').textContent   = gastos.length + ' lançamento' + (gastos.length !== 1 ? 's' : '');

  const total = dados.reduce((s, m) => s + m.valor, 0);
  document.getElementById('media-geral').textContent  = dados.length ? fmt(total / dados.length) : '—';
}

/*
  setOrdenacao(valor)
  ──────────────────────
  Chamada pelo onchange do <select> de ordenação.
  Apenas atualiza o estado e re-renderiza a lista — a ordenação
  em si acontece dentro de renderLista(), na função ordenarDados().
*/
function setOrdenacao(valor) {
  ordenacaoAtiva = valor;
  paginaAtual = 1; // muda a ordenação, volta pra primeira página
  renderLista();
}

/*
  ordenarDados(dados)
  ──────────────────────
  Aplica a ordenação escolhida sobre uma cópia do array
  (nunca ordena o array original — evita efeitos colaterais
  em outras partes do código que dependem da ordem de 'todos').
*/
function ordenarDados(dados) {
  const copia = [...dados];

  switch (ordenacaoAtiva) {
    case 'recente':
      return copia.sort((a, b) => new Date(b.data) - new Date(a.data));
    case 'antigo':
      return copia.sort((a, b) => new Date(a.data) - new Date(b.data));
    case 'maior':
      return copia.sort((a, b) => b.valor - a.valor);
    case 'menor':
      return copia.sort((a, b) => a.valor - b.valor);
    default:
      return copia;
  }
}

function alternarListaCompleta() {
  listaCompleta = !listaCompleta;
  paginaAtual = 1;
  renderLista();
}

function renderLista() {
  // getDadosFiltrados() já aplica tipo + período juntos
  const busca = document.getElementById('busca-movimentacoes').value.trim().toLocaleLowerCase('pt-BR');
  const dados = getDadosFiltrados().filter(m => `${m.descricao || ''} ${m.categoria || ''}`.toLocaleLowerCase('pt-BR').includes(busca));
  document.getElementById('movimentacoes-titulo').textContent = listaCompleta || busca || filtroAtivo !== 'TODOS' ? 'Movimentações' : 'Movimentações recentes';
  const verTodas = document.getElementById('ver-todas');
  verTodas.hidden = dados.length <= ITENS_POR_PAGINA;
  verTodas.textContent = listaCompleta ? 'Mostrar apenas 5' : `Ver todas (${dados.length})`;
  if (!listaCompleta) paginaAtual = 1;
  const lista = document.getElementById('lista');
  document.getElementById('list-count').textContent = dados.length + ' item' + (dados.length !== 1 ? 's' : '');
  lista.innerHTML = '';

  if (!dados.length) {
    lista.innerHTML = `<div class="empty"><div class="empty-icon">📋</div><div class="empty-text">Nenhuma movimentação encontrada para este filtro.</div></div>`;
    document.getElementById('paginacao').innerHTML = ''; // some com a paginação quando não há dados
    return;
  }

  const sorted = ordenarDados(dados);

  /*
    PAGINAÇÃO
    ───────────
    1. Calcula quantas páginas existem no total
    2. Garante que paginaAtual não "sobre" do limite (ex: usuário
       estava na página 5, aplicou um filtro que reduziu pra 2 páginas)
    3. Fatia o array (slice) só com os itens da página atual
  */
  const totalPaginas = Math.max(1, Math.ceil(sorted.length / ITENS_POR_PAGINA));
  if (paginaAtual > totalPaginas) paginaAtual = totalPaginas;

  const inicio = (paginaAtual - 1) * ITENS_POR_PAGINA;
  const fim = inicio + ITENS_POR_PAGINA;
  const paginaDeItens = sorted.slice(inicio, fim);

  paginaDeItens.forEach(m => {
    const isGanho = m.tipo === 'GANHO';
    const div = document.createElement('div');
    div.className = `mov-item ${isGanho ? 'ganho-item' : 'gasto-item'}`;
    div.innerHTML = `
      <div class="mov-left">
        <div class="mov-icon" style="background:${isGanho ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)'}">
          ${isGanho ? '↑' : '↓'}
        </div>
        <div>
          <div class="mov-desc">${escaparHtml(m.descricao || m.categoria)}</div>
          <div class="mov-meta">
            <span class="mov-badge">${escaparHtml(m.categoria)}</span>
            <span class="mov-date">${fmtData(m.data)}</span>
          </div>
        </div>
      </div>
      <div class="mov-right">
        <div>
          <div class="mov-value ${isGanho ? 'green' : 'red'}">${isGanho ? '+' : '-'} ${fmt(m.valor)}</div>
          <div class="mov-value-label">${isGanho ? 'entrada' : 'saída'}</div>
        </div>
        <div class="mov-actions"><button class="btn-edit btn-edit-item"
          data-id="${m.id}"
          data-categoria="${escaparHtml(m.categoria)}"
          data-descricao="${escaparHtml(m.descricao || '')}"
          data-valor="${m.valor}"
          data-tipo="${m.tipo}"
          data-data="${m.data}"
          aria-label="Editar movimentação" title="Editar"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m15 4 5 5M4 20l5-1L20 8a2 2 0 0 0-5-5L4 14v6Z"/></svg></button>
        <button class="btn-delete btn-del-item"
          data-id="${m.id}"
          data-desc="${escaparHtml(m.descricao || m.categoria)}"
          data-valor="${m.valor}"
          data-tipo="${m.tipo}"
          aria-label="Excluir movimentação" title="Excluir"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 10v7m4-7v7"/></svg></button></div>
      </div>`;
    lista.appendChild(div);
  });

  renderPaginacao(listaCompleta ? totalPaginas : 1);
}

/*
  renderPaginacao(totalPaginas)
  ─────────────────────────────────
  Desenha os controles de página: ◀ [1] [2] [3] ... [N] ▶

  ESTRATÉGIA DE RETICÊNCIAS:
  Com poucas páginas (≤ 7), mostra todos os números.
  Com muitas páginas, mostra: primeira, última, a atual e suas
  vizinhas — e "..." no lugar dos números pulados. Isso evita
  uma barra horizontal gigante quando há, por exemplo, 40 páginas.

  Se houver só 1 página, o container fica vazio (sem controles).
*/
function renderPaginacao(totalPaginas) {
  const container = document.getElementById('paginacao');

  if (totalPaginas <= 1) {
    container.innerHTML = '';
    return;
  }

  let html = '';

  // Botão "anterior" — desabilitado na primeira página
  html += `<button class="page-btn" ${paginaAtual === 1 ? 'disabled' : ''} onclick="irParaPagina(${paginaAtual - 1})">‹</button>`;

  /*
    Decide quais números de página mostrar.
    Sempre inclui: página 1, página atual (-1/+1) e última página.
    Tudo que não estiver nesse conjunto vira "..." (no máximo
    uma reticência entre cada bloco de números visíveis).
  */
  const paginasVisiveis = new Set([1, totalPaginas, paginaAtual, paginaAtual - 1, paginaAtual + 1]);
  let ultimoNumeroExibido = 0;

  for (let p = 1; p <= totalPaginas; p++) {
    if (!paginasVisiveis.has(p)) continue;

    // Se pulamos números desde o último exibido, insere reticências
    if (p - ultimoNumeroExibido > 1) {
      html += `<span class="page-ellipsis">…</span>`;
    }

    html += `<button class="page-btn ${p === paginaAtual ? 'active' : ''}" onclick="irParaPagina(${p})">${p}</button>`;
    ultimoNumeroExibido = p;
  }

  // Botão "próximo" — desabilitado na última página
  html += `<button class="page-btn" ${paginaAtual === totalPaginas ? 'disabled' : ''} onclick="irParaPagina(${paginaAtual + 1})">›</button>`;

  container.innerHTML = html;
}

/*
  irParaPagina(numero)
  ───────────────────────
  Atualiza o estado da página atual e re-renderiza só a lista
  (não precisa re-rodar stats/saldo/gráfico, que não mudam
  com a paginação — só renderLista() é necessário aqui).
*/
function irParaPagina(numero) {
  paginaAtual = numero;
  renderLista();

  // Rola suavemente até o topo da lista — útil em telas pequenas
  // onde a lista é longa e o usuário mudaria de página "às cegas"
  document.querySelector('.list-header').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderChart() {
  const area = document.getElementById('chart-area');
  const gastos = todos.filter(m => dentroDoPeriodo(m.data) && m.tipo === 'GASTO');

  if (!gastos.length) {
    area.innerHTML = '<div style="color:var(--muted);font-size:12px;text-align:center;padding:12px 0;">Sem gastos registrados</div>';
    return;
  }

  const totais = {};
  gastos.forEach(g => { totais[g.categoria] = (totais[g.categoria] || 0) + g.valor; });
  const totalGastos = Object.values(totais).reduce((soma, valor) => soma + valor, 0);
  const sorted = Object.entries(totais).sort((a, b) => b[1] - a[1]).slice(0, 6);

  area.innerHTML = sorted.map(([cat, val]) => {
    const pct = Math.round((val / totalGastos) * 100);
    return `
      <div class="chart-row">
        <div class="chart-cat">${escaparHtml(cat)}</div>
        <div class="chart-bar-bg">
          <div class="chart-bar-fill" data-pct="${pct}" style="background:var(--accent);"></div>
        </div>
        <div class="chart-pct" title="${fmt(val)}">${pct}%</div>
      </div>`;
  }).join('');

  requestAnimationFrame(() => {
    document.querySelectorAll('.chart-bar-fill').forEach(el => { el.style.width = el.dataset.pct + '%'; });
  });
}

/*
  EVENT DELEGATION no lugar de onclick inline
  ────────────────────────────────────────────
  Em vez de colocar onclick em cada botão gerado dinamicamente,
  colocamos UM listener no elemento pai (#lista).
  Quando qualquer clique acontece dentro da lista, verificamos
  se o alvo (e.target) tem a classe .btn-del-item.
  Se sim, lemos os data attributes e abrimos o modal.

  Vantagem: não há risco de quebrar com aspas ou caracteres
  especiais na descrição, pois os dados ficam em atributos
  HTML escapados — não em strings JavaScript inline.
*/
document.getElementById('lista').addEventListener('click', function(e) {
  const btn = e.target.closest('.btn-del-item');
  if (!btn) return;

  const id    = btn.dataset.id;
  const desc  = btn.dataset.desc;
  const valor = parseFloat(btn.dataset.valor);
  const tipo  = btn.dataset.tipo;

  // Preenche o preview com os dados do item
  document.getElementById('modal-preview-desc').textContent  = desc;
  document.getElementById('modal-preview-valor').textContent =
    (tipo === 'GANHO' ? '+ ' : '- ') + fmt(valor) + ' · ' + tipo;

  // Grava o id no botão confirmar
  document.getElementById('btn-confirmar-delete').dataset.id = id;

  // Abre o modal
  document.getElementById('modal').classList.add('open');
  document.body.style.overflow = 'hidden';
});

/*
  fecharModal()
  ─────────────
  Remove a classe .open — o modal some.
  Também restaura o scroll do body.
*/
function fecharModal() {
  document.getElementById('modal').classList.remove('open');
  document.body.style.overflow = '';
}

/*
  confirmarDeletar()
  ──────────────────
  Executado quando o usuário clica "Sim, excluir".
  Lê o id do data attribute, faz o DELETE e recarrega.
*/
async function confirmarDeletar() {
  const id = document.getElementById('btn-confirmar-delete').dataset.id;

  // Fecha o modal imediatamente — não espera o fetch.
  // Isso dá feedback visual instantâneo ao usuário.
  fecharModal();

  try {
    const res = await apiFetch(`${API}/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      toast(`Falha ao excluir (erro ${res.status}).`, 'error');
      return;
    }
    removerMovimentacaoLocal(id);
    atualizarTudo();
    toast('Movimentação excluída.', 'success');
  } catch (e) {
    toast('Erro ao conectar com a API.', 'error');
    console.error('Erro ao excluir:', e);
  }
}

// Init
const hoje = new Date();
document.getElementById('data-hoje').textContent = hoje.toLocaleDateString('pt-BR', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
atualizarPerfilNoHeader();
document.getElementById('data').value = dataLocalISO(hoje);
document.getElementById('valor').addEventListener('keydown', e => { if (e.key === 'Enter') salvar(); });
document.addEventListener('click', event => {
  if (!document.getElementById('profile-menu').contains(event.target)) fecharMenuPerfil();
  if (!document.getElementById('export-menu').contains(event.target)) fecharMenuExportacao();
  if (!document.querySelector('.space-switcher').contains(event.target)) fecharSeletorEspacos();
});
document.getElementById('dialog-espacos').addEventListener('click', event => {
  if (event.target === event.currentTarget) fecharEspacos();
});

/*
  Fechar modal clicando no overlay (fora do box)
  ───────────────────────────────────────────────
  O evento de clique sobe pelo DOM (bubbling).
  Se o clique veio direto no overlay (e.target === overlay),
  fechamos. Se veio de dentro do .modal-box, ignoramos.
  Essa checagem de e.target evita fechar ao clicar dentro do painel.
*/
document.getElementById('modal').addEventListener('click', function(e) {
  if (e.target === this) fecharModal();
});

/*
  Fechar com tecla Escape
  ───────────────────────
  Padrão de acessibilidade para modais (WCAG).
  Qualquer modal profissional deve suportar isso.
*/
// ── MODAL DE EDIÇÃO ───────────────────────────────────────────

// Tipo selecionado dentro do modal de edição
let tipoEdit = 'GANHO';

// Atualiza o toggle visual e a cor do botão salvar dentro do modal
function setTipoEdit(tipo) {
  tipoEdit = tipo;
  document.getElementById('edit-btn-ganho').classList.toggle('active', tipo === 'GANHO');
  document.getElementById('edit-btn-gasto').classList.toggle('active', tipo === 'GASTO');
  const btn = document.getElementById('btn-salvar-edit');
  btn.className = `btn-modal ${tipo === 'GANHO' ? 'salvar-ganho' : 'salvar-gasto'}`;
}

function fecharModalEdit() {
  document.getElementById('modal-edit').classList.remove('open');
  document.body.style.overflow = '';
}

function limparErroEdicao() {
  const el = document.getElementById('edit-error');
  el.style.display = 'none';
  el.textContent = '';
}

function mostrarErroEdicao(mensagem) {
  const el = document.getElementById('edit-error');
  el.textContent = mensagem;
  el.style.display = 'block';
}

// Lê os data-attributes do botão ✎, preenche o formulário e abre o modal
document.getElementById('lista').addEventListener('click', function(e) {
  const btn = e.target.closest('.btn-edit-item');
  if (!btn) return;

  // Preenche os campos com os dados atuais do item
  document.getElementById('edit-categoria').value  = btn.dataset.categoria;
  document.getElementById('edit-descricao').value  = btn.dataset.descricao;
  document.getElementById('edit-valor').value      = btn.dataset.valor;
  document.getElementById('edit-data').value       = btn.dataset.data;

  // Define o tipo e atualiza o visual do toggle
  setTipoEdit(btn.dataset.tipo);
  limparErroEdicao();

  // Grava o id no botão salvar para usar no PUT
  document.getElementById('btn-salvar-edit').dataset.id = btn.dataset.id;

  // Abre o modal
  document.getElementById('modal-edit').classList.add('open');
  document.body.style.overflow = 'hidden';

  // Foca no primeiro campo para facilitar a edição
  setTimeout(() => document.getElementById('edit-categoria').focus(), 100);
});

// Envia o PUT para a API com os dados editados
async function confirmarEdicao() {
  const botao     = document.getElementById('btn-salvar-edit');
  const id        = document.getElementById('btn-salvar-edit').dataset.id;
  const categoria = document.getElementById('edit-categoria').value.trim();
  const descricao = document.getElementById('edit-descricao').value.trim() || null;
  const valor     = parseFloat(document.getElementById('edit-valor').value);
  const data      = document.getElementById('edit-data').value;

  if (!categoria || !valor || valor <= 0 || !data) {
    if (!categoria) document.getElementById('edit-categoria').focus();
    else if (!data) document.getElementById('edit-data').focus();
    else document.getElementById('edit-valor').focus();
    return;
  }

  limparErroEdicao();
  const textoOriginal = botao.textContent;
  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    const res = await apiFetch(`${API}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tipo: tipoEdit, categoria, descricao, valor, data }),
      timeoutMs: 12000,
    });

    if (!res.ok) {
      let corpo = null;
      try {
        corpo = await res.json();
      } catch (_) {}

      const mensagem = mensagemHttp(res.status, corpo, 'Não foi possível atualizar a movimentação.');
      mostrarErroEdicao(mensagem);
      toast(mensagem, 'error');
      return;
    }

    const corpo = await res.json();
    await carregar();
    fecharModalEdit();
    toast(corpo?.message || 'Movimentação atualizada com sucesso.', 'success');
  } catch (e) {
    if (e.message === 'Sessão expirada') return;

    const mensagem = e.message === 'request_timeout'
      ? 'Tempo de espera excedido. Verifique sua conexão e tente novamente.'
      : 'Falha de conexão com a API. Tente novamente.';
    mostrarErroEdicao(mensagem);
    toast(mensagem, 'error');
  } finally {
    botao.disabled = false;
    botao.textContent = textoOriginal;
  }
}

// Fechar modal-edit clicando no overlay
document.getElementById('modal-edit').addEventListener('click', function(e) {
  if (e.target === this) fecharModalEdit();
});

// Escape fecha qualquer modal aberto
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    fecharModal();
    fecharModalEdit();
  }
});

let resizeDashboardTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeDashboardTimer);
  resizeDashboardTimer = setTimeout(() => { if (todos.length) renderEvolucao(); }, 120);
});
inicializarAplicacao();
