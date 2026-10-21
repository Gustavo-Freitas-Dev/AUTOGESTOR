/* Categorias do registro rápido — sem alterar contratos da API. */
(() => {
  const base = ['Alimentação','Mercado','Moradia','Transporte','Saúde','Educação','Lazer','Assinaturas','Salário','Freelance','Outros'];
  const key = 'autogestor_categorias_personalizadas';
  const root = document.getElementById('category-picker');
  if (!root) return;
  const trigger = document.getElementById('category-trigger');
  const menu = document.getElementById('category-menu');
  const field = document.getElementById('categoria');
  const selected = document.getElementById('category-selected');
  const search = document.getElementById('category-search');
  const options = document.getElementById('category-options');
  const newField = document.getElementById('category-new');
  const add = document.getElementById('category-add');
  let remote = [];
  let loadedSpace = null;
  const space = () => typeof ESPACO_ATUAL !== 'undefined' ? ESPACO_ATUAL?.id : null;
  const endpoint = () => '/espacos/' + space() + '/categorias/';
  const headers = () => ({ Authorization: 'Bearer ' + (localStorage.getItem('autogestor_token') || '') });
  function customs() { return remote.map(item => item.nome); }
  async function load() {
    const id=space(); if(!id)return;
    loadedSpace=null;remote=[];render();
    try {
      const response=await fetch(endpoint(),{headers:headers()});
      if(!response.ok)throw Error('Falha ao carregar categorias ('+response.status+').');
      remote=await response.json();loadedSpace=id;
      const legacy=JSON.parse(localStorage.getItem(key)||'[]');
      if(Array.isArray(legacy)) {
        let failed=false;
        for(const name of legacy.filter(x=>typeof x==='string'&&x.trim())) {
          if(base.some(x=>x.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR')) || remote.some(x=>x.nome.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR')))continue;
          const result=await fetch(endpoint(),{method:'POST',headers:{...headers(),'Content-Type':'application/json'},body:JSON.stringify({nome:name})});
          if(result.ok)remote.push(await result.json());
          else if(result.status===409) {const refresh=await fetch(endpoint(),{headers:headers()});if(refresh.ok)remote=await refresh.json();else failed=true;}
          else failed=true;
        }
        if(!failed)localStorage.removeItem(key);
      }
    } catch(err) {loadedSpace=null;console.error(err);window.alert('Não foi possível sincronizar categorias. Tente novamente antes de criar ou excluir.');}
    render();
  }
  function all() { return [...new Set([...base,...customs()])].sort((a, b) => a.localeCompare(b, 'pt-BR', { sensitivity: 'base' })); }
  function render() {
    options.replaceChildren();
    const q=search.value.trim().toLocaleLowerCase('pt-BR');
    const matches=all().filter(x=>x.toLocaleLowerCase('pt-BR').includes(q));
    if (!matches.length) { const p=document.createElement('p');p.className='category-hint';p.textContent='Nenhuma categoria encontrada';options.append(p); }
    matches.forEach(name => {
      const row=document.createElement('div');row.className='category-option-row';
      const b=document.createElement('button');b.type='button';b.className='category-option';b.setAttribute('role','option');b.setAttribute('aria-selected',String(field.value===name));b.textContent=name;
      b.addEventListener('click',()=>{field.value=name;selected.textContent=name;close();trigger.focus();});row.append(b);
      const custom=remote.some(x=>x.nome.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR'))&&!base.some(x=>x.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR'));
      if(custom) {
        const remove=document.createElement('button');remove.type='button';remove.className='category-delete';remove.textContent='×';remove.title='Excluir categoria '+name;remove.setAttribute('aria-label','Excluir categoria '+name);
        remove.addEventListener('click',async()=>{
          if(!window.confirm('Excluir a categoria "'+name+'"? As movimentações existentes não serão apagadas.'))return;
          if(loadedSpace!==space()){window.alert('Aguarde o carregamento das categorias.');return;}
          const item=remote.find(x=>x.nome.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR'));
          try {const response=await fetch(endpoint()+item.id,{method:'DELETE',headers:headers()});if(!response.ok)throw Error();remote=remote.filter(x=>x.id!==item.id);}
          catch {window.alert('Não foi possível excluir a categoria.');return;}
          if(field.value.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR')){field.value='';selected.textContent='Selecione uma categoria';}
          render();
        });row.append(remove);
      }
      options.append(row);
    });
  }
  function open() { menu.hidden=false;trigger.setAttribute('aria-expanded','true');render();search.focus(); }
  function close() { menu.hidden=true;trigger.setAttribute('aria-expanded','false');search.value=''; }
  trigger.addEventListener('click',()=>menu.hidden?open():close());
  search.addEventListener('input',render);
  add.addEventListener('click',async()=>{
    const name=newField.value.trim().replace(/\s+/g,' ');
    if(!name || name.length>80) { newField.focus();return; }
    const existing=all().find(x=>x.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR'));
    const chosen=existing||name;
    if(!existing) {
      if(loadedSpace!==space()){window.alert('Aguarde a sincronização das categorias.');return;}
      try {const response=await fetch(endpoint(),{method:'POST',headers:{...headers(),'Content-Type':'application/json'},body:JSON.stringify({nome:name})});if(!response.ok)throw Error();remote.push(await response.json());}
      catch {window.alert('Não foi possível salvar a categoria.');return;}
    }
    field.value=chosen;selected.textContent=chosen;newField.value='';close();trigger.focus();
  });
  newField.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();add.click();}});
  document.addEventListener('pointerdown',e=>{if(!root.contains(e.target))close();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!menu.hidden){close();trigger.focus();}});
  // O fluxo original limpa o campo ao salvar; refletir essa mudança no botão.
  document.addEventListener('autogestor:category-reset',()=>{selected.textContent='Selecione uma categoria';});
  const observer=new MutationObserver(()=>{if(!field.value&&selected.textContent!=='Selecione uma categoria')selected.textContent='Selecione uma categoria';});
  observer.observe(field,{attributes:true,attributeFilter:['value']});
  const save=document.getElementById('btn-salvar');
  if(save)save.addEventListener('click',()=>{setTimeout(()=>{if(!field.value)selected.textContent='Selecione uma categoria';},400);});
  document.addEventListener('autogestor:space-changed',load);
  window.focusCategoriaRegistro=()=>{open();};
  load();
})();
