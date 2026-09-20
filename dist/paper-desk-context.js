import {flowNeighbours} from './paper-flow.js';

const status = note => note.liveDraft ? 'Current editor' : note.writing_status === 'complete' ? 'Approved' : note.fields?.['Manuscript prose']?.trim() ? 'Draft saved' : 'To write';

export function readingContextShell() {
 return `<aside id="desk-reading-context" class="desk-reading-context" aria-label="Reading context" hidden>
  <div class="desk-context-heading"><h2 id="desk-context-title" tabindex="-1">Reading context</h2><button class="btn quiet" id="desk-context-close" aria-label="Close reading context">×</button></div>
  <div class="desk-context-modes" aria-label="Choose reading context"><button class="btn quiet" data-context-mode="previous" aria-pressed="false">Previous part</button><button class="btn quiet" data-context-mode="outline" aria-pressed="false">Paper outline</button></div>
  <div id="desk-context-content" class="desk-context-content"></div>
  <button class="btn quiet desk-context-return" id="desk-context-return">Return to my draft</button>
 </aside>`;
}

export function contextPreviewHTML(note, esc, title = value => value, {showTitle = true} = {}) {
 const fields = note.fields || {}, prose = fields['Manuscript prose'] || '';
 return `<article class="desk-context-preview">${showTitle ? `<h3>${esc(title(note.title))}</h3>` : ''}
  <p class="desk-context-state">${esc(status(note))} · read only here</p>
  ${prose.trim() ? `<div class="desk-context-prose" tabindex="0" aria-label="Manuscript text for ${esc(title(note.title))}">${esc(prose)}</div>` : '<p class="desk-context-empty">No manuscript text yet. This part stays in its place in the outline.</p>'}
  ${fields.Purpose || fields['Main message'] || fields['Notes and bullet points'] ? `<details><summary>Purpose and argument notes</summary>${fields.Purpose || fields['Main message'] ? `<p>${esc(fields.Purpose || fields['Main message'])}</p>` : ''}${fields['Notes and bullet points'] ? `<div class="desk-context-notes">${esc(fields['Notes and bullet points'])}</div>` : ''}</details>` : ''}
  ${!note.liveDraft ? `<button class="btn secondary" data-context-edit="${esc(note.id)}">Open this part for editing</button>` : ''}
 </article>`;
}

export function contextOutlineHTML(plan, currentId, esc, title = value => value) {
 const numbers = new Map(plan.nodes.filter(n => n.type === 'argument').map((n, i) => [n.id, i + 1]));
 const ancestors = new Set();
 let n = plan.nodes.find(n => n.id === currentId);
 while (n?.parent_id && !ancestors.has(n.parent_id)) { ancestors.add(n.parent_id); n = plan.nodes.find(p => p.id === n.parent_id); }
 const draw = (parent, seen = new Set()) => plan.nodes.filter(n => (n.parent_id || null) === parent && !seen.has(n.id)).map(n => {
  if (n.type !== 'argument') return `<li><details class="desk-context-group" ${ancestors.has(n.id) ? 'open' : ''}><summary>${esc(title(n.title))}</summary><ol>${draw(n.id, new Set([...seen, n.id]))}</ol></details></li>`;
  const here = n.id === currentId;
  return `<li><details class="desk-context-item" data-context-card="${esc(n.id)}"><summary ${here ? 'aria-current="location"' : ''}><span class="desk-context-number">${numbers.get(n.id)}.</span><span><strong>${esc(title(n.title))}</strong><small data-context-status="${esc(n.id)}">${here ? 'You are writing here' : esc(status(n))}</small></span></summary><div data-context-preview="${esc(n.id)}"></div></details></li>`;
 }).join('');
 // Root arguments are supported, as well as sections containing subsections.
 return `<p class="desk-context-hint">${numbers.size} writing parts in manuscript order. Expand a part to read its text.</p><ol class="desk-context-outline">${draw(null)}</ol>`;
}

// An independent read channel: no save, approval, or navigation is performed here.
// Changing view or leaving the editor invalidates late responses, including failures.
export function createContextReader({api, paperId, current = () => true}) {
 let generation = 0;
 return {
  cancel() { generation++; },
  async load(cardId) {
   const request = ++generation;
   try {
    const value = await api(`/workspace/papers/${encodeURIComponent(paperId)}/cards/${encodeURIComponent(cardId)}`);
    return request === generation && current() ? value : null;
   } catch (error) { if (request === generation && current()) throw error; return null; }
  }
 };
}

export function mountReadingContext({host, body, editor, plan, noteId, api, esc, title, getCurrentNote, go, current, onMode = () => {}}) {
 const content = host.querySelector('#desk-context-content'), heading = host.querySelector('#desk-context-title');
 const reader = createContextReader({api, paperId: plan.id, current});
 const controls = new AbortController();
 let mode = null, alive = true, selection = null, editorScroll = 0;
 const active = () => alive && current();
 const remember = () => { selection = [editor.selectionStart, editor.selectionEnd, editor.selectionDirection]; editorScroll = editor.scrollTop; };
 const focusTarget = target => { target.focus({preventScroll: true}); if (matchMedia('(max-width:760px)').matches) target.scrollIntoView({block: 'nearest'}); };
 const returnToDraft = () => { focusTarget(editor); if (selection) editor.setSelectionRange(...selection); editor.scrollTop = editorScroll; };
 editor.addEventListener('select', remember, {signal: controls.signal});
 editor.addEventListener('input', remember, {signal: controls.signal});
 editor.addEventListener('blur', remember, {signal: controls.signal});
 const syncButtons = () => { host.querySelectorAll('[data-context-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.contextMode === mode))); onMode(mode); };
 function close() { reader.cancel(); mode = null; host.hidden = true; body.classList.remove('desk-context-open'); syncButtons(); returnToDraft(); }
 function bindEdit(root) { root.querySelectorAll('[data-context-edit]').forEach(b => { b.onclick = () => go(b.dataset.contextEdit); }); }
 async function preview(cardId, target) {
  target.innerHTML = '<p class="desk-context-hint" role="status">Loading saved text…</p>';
  try {
   const note = cardId === noteId ? {...getCurrentNote(), liveDraft: true} : await reader.load(cardId);
   if (!active() || !note || !target.isConnected) return;
   target.innerHTML = contextPreviewHTML(note, esc, title, {showTitle: !target.closest('[data-context-card]')}); bindEdit(target);
   const label = target.closest('[data-context-card]')?.querySelector('[data-context-status]');
   if (label && cardId !== noteId) label.textContent = status(note);
  } catch (e) {
   if (!active() || !target.isConnected) return;
   target.innerHTML = `<p role="status">Could not load this text: ${esc(e.message)}</p><button class="btn quiet" data-context-retry>Try again</button>`;
   target.querySelector('[data-context-retry]').onclick = () => preview(cardId, target);
  }
 }
 function outline() {
  const snapshot = {...plan, nodes: plan.nodes.map(n => n.id === noteId ? {...n, ...getCurrentNote(), liveDraft: true} : n)};
  content.innerHTML = contextOutlineHTML(snapshot, noteId, esc, title);
  content.querySelectorAll('[data-context-card]').forEach(detail => {
   detail.addEventListener('toggle', () => {
    if (mode !== 'outline' || !detail.isConnected) return;
    if (detail.open) {
     // Keep just one manuscript preview open to avoid a wall of repeated drafts.
     content.querySelectorAll('[data-context-card]').forEach(other => { if (other !== detail) other.open = false; });
     reader.cancel(); preview(detail.dataset.contextCard, detail.querySelector('[data-context-preview]'));
    }
   }, {signal: controls.signal});
  });
 }
 function open(nextMode, {focus = true} = {}) {
  if (!active()) return;
  reader.cancel(); mode = nextMode; host.hidden = false; body.classList.add('desk-context-open');
  heading.textContent = mode === 'previous' ? 'Previous part' : 'Paper outline'; syncButtons();
  if (mode === 'previous') {
   const previous = flowNeighbours(plan, noteId).before;
   content.innerHTML = '<div id="desk-previous-text"></div>';
   if (previous) preview(previous.id, content.firstElementChild);
   else content.innerHTML = '<p class="desk-context-empty">You are writing the first part. There is no previous part yet.</p>';
  } else outline();
  if (focus) focusTarget(heading);
 }
 host.querySelectorAll('[data-context-mode]').forEach(b => { b.onclick = () => open(b.dataset.contextMode); });
 host.querySelector('#desk-context-close').onclick = close;
 host.querySelector('#desk-context-return').onclick = returnToDraft;
 host.addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); } }, {signal: controls.signal});
 editor.addEventListener('input', () => {
  if (mode !== 'outline') return;
  const detail = [...content.querySelectorAll('[data-context-card]')].find(d => d.dataset.contextCard === noteId);
  if (detail?.open) {
   const prose = detail.querySelector('.desk-context-prose');
   if (prose && editor.value.trim()) prose.textContent = editor.value;
   else preview(noteId, detail.querySelector('[data-context-preview]'));
  }
 }, {signal: controls.signal});
 return {open, close, toggle(nextMode) { mode === nextMode ? close() : open(nextMode); }, dispose() {alive = false; reader.cancel(); controls.abort();}};
}
