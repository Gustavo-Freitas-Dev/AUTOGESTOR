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
  function customs() { try { const a=JSON.parse(localStorage.getItem(key)||'[]'); return Array.isArray(a)?a.filter(x=>typeof x==='string'):[]; } catch { return []; } }
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
      const custom=customs().some(x=>x.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR'))&&!base.some(x=>x.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR'));
      if(custom) {
        const remove=document.createElement('button');remove.type='button';remove.className='category-delete';remove.textContent='×';remove.title='Excluir categoria '+name;remove.setAttribute('aria-label','Excluir categoria '+name);
        remove.addEventListener('click',()=>{
          if(!window.confirm('Excluir a categoria "'+name+'"? As movimentações existentes não serão apagadas.'))return;
          try {localStorage.setItem(key,JSON.stringify(customs().filter(x=>x.toLocaleLowerCase('pt-BR')!==name.toLocaleLowerCase('pt-BR'))));}
          catch {window.alert('Não foi possível excluir a categoria neste navegador.');return;}
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
  add.addEventListener('click',()=>{
    const name=newField.value.trim().replace(/\s+/g,' ');
    if(!name || name.length>80) { newField.focus();return; }
    const existing=all().find(x=>x.toLocaleLowerCase('pt-BR')===name.toLocaleLowerCase('pt-BR'));
    const chosen=existing||name;
    if(!existing) {try{localStorage.setItem(key,JSON.stringify([...customs(),name]));}catch{ /* Storage indisponível: seleção ainda funciona */ }}
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
  window.focusCategoriaRegistro=()=>{open();};
})();
