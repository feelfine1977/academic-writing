export function mountSidebar(){
 const sidebar=document.querySelector('.sidebar');if(!sidebar)return;
 const key='awl-sidebar-collapsed';let collapsed=false;
 sidebar.querySelector('.brand')?.setAttribute('aria-label','Academic Writing Lab home');
 try{collapsed=localStorage.getItem(key)==='true'}catch{}
 sidebar.id='workspace-menu';
 const button=document.createElement('button');button.type='button';button.id='sidebar-toggle';button.className='sidebar-toggle';button.setAttribute('aria-controls','navigation');
 sidebar.prepend(button);
 for(const link of sidebar.querySelectorAll('#navigation a')){
  const name=link.textContent.replace(link.querySelector('.nav-icon')?.textContent||'','').trim();link.title=name;link.setAttribute('aria-label',name);
  const label=document.createElement('span');label.className='nav-label';
  for(const n of [...link.childNodes])if(n.nodeType===Node.TEXT_NODE)label.append(n);
  link.append(label);link.querySelector('.nav-icon')?.setAttribute('aria-hidden','true');
 }
 const settings=sidebar.querySelector('.settings-link');settings.setAttribute('aria-label','Settings & backups');settings.title='Settings & backups';
 function apply(){
  document.body.classList.toggle('sidebar-collapsed',collapsed);button.setAttribute('aria-expanded',String(!collapsed));
  button.setAttribute('aria-label',collapsed?'Expand navigation':'Minimise navigation');button.title=collapsed?'Expand navigation':'Minimise navigation';
  button.innerHTML=`<span aria-hidden="true">${collapsed?'☰':'‹'}</span><span class="sidebar-toggle-label">Minimise menu</span>`;
 }
 button.onclick=()=>{collapsed=!collapsed;try{localStorage.setItem(key,String(collapsed))}catch{}apply()};
 window.addEventListener('storage',event=>{if(event.key===key){collapsed=event.newValue==='true';apply()}});apply();
}
