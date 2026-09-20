// Academic and fiction work areas; older deep links keep their saved context.
export const pageLabels={'section-writing':'Section writing',reading:'Reading documents',learning:'Overview',today:'Overview',courses:'Courses',practice:'Practice',writing:'Saved answers',progress:'Progress',resources:'Resources',library:'Research notes',phrasebook:'Academic phrasebook',papers:'Projects',paper:'Earlier writing workspace',revision:'Source discussions',reader:'Source-card feedback',settings:'Tutor & backups',obsidian:'Obsidian & devices',guide:'How to use the lab',comments:'My questions & comments'};
const groups={
 reading:{title:'Reading & notes',links:[]},
 fiction:{title:'Fiction workshop',links:[]},
 learning:{title:'Learning',links:[['learning','Overview'],['courses','Courses'],['practice','Practice'],['writing','Saved answers'],['progress','Progress'],['resources','Resources']]},
 papers:{title:'Papers',links:[]},
 settings:{title:'Settings',links:[['settings','Tutor & backups'],['obsidian','Obsidian & devices']]},
 help:{title:'Help',links:[['guide','How to use the lab'],['comments','My questions & comments']]}
};
export function navigationFor(page){
 const group=page==='reading'?'reading':page==='fiction'?'fiction':['papers','paper','revision','reader','section-writing'].includes(page)?'papers':['settings','obsidian'].includes(page)?'settings':['guide','comments'].includes(page)?'help':'learning';
 const selected=page==='today'?'learning':['library','phrasebook'].includes(page)?'resources':page;
 return {...groups[group],group,selected,label:pageLabels[page]||pageLabels.learning};
}
export function renderNavigation(page,esc){
 const n=navigationFor(page),host=document.querySelector('#section-navigation');
 document.querySelector('.crumb').textContent=n.title;
 document.querySelector('#page-label').textContent=n.label;
 document.querySelectorAll('[data-area]').forEach(a=>{const current=a.dataset.area===n.group;a.classList.toggle('active',current);current?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current')});
 host.hidden=!n.links.length;
 host.setAttribute('aria-label',n.title+' navigation');
 host.innerHTML=n.links.map(([key,label])=>`<a href="#${key}" ${key===n.selected?'class="active" aria-current="page"':''}>${esc(label)}</a>`).join('');
 document.body.dataset.workspaceArea=n.group;
}
