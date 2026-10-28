'use strict';
const $=id=>document.getElementById(id), NS='http://www.w3.org/2000/svg';
const kinds={book:{name:'Answers from the document',short:'From the document',color:'var(--pg-blue)'},scope:{name:'Refuses off-topic requests',short:'Off-topic refused',color:'var(--pg-olive)'},handling:{name:'Handles tricky inputs',short:'Tricky inputs',color:'var(--pg-gold)'},knowledge:{name:'Beyond the booklet',short:'Beyond the booklet'}};
const factualNames={correct:'Correct',incorrect_or_incomplete:'Wrong or incomplete',unanswered:'Not answered',unverified_detail:'Adds unverified detail',not_applicable:'Scored on behaviour, not facts'};
const factualColors=['var(--pg-blue)','var(--pg-gold)','var(--pg-pink)','var(--pg-olive)'];
const dates={'2026-10-27-original':{short:'27 Oct',long:'27 October 2026'},'2026-10-28-compatible-runtime':{short:'28 Oct',long:'28 October 2026'}};
let active='overview';
function node(tag,value,cls){const n=document.createElement(tag);if(value!==undefined)n.textContent=value;if(cls)n.className=cls;return n;}
function svg(tag,attrs,value){const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);if(value!==undefined)n.textContent=value;return n;}
function add(s,tag,attrs,value){const n=svg(tag,attrs,value);s.append(n);return n;}
function label(s,x,y,value,anchor='start',size=12,muted=false){return add(s,'text',{x,y,'text-anchor':anchor,'font-size':size,fill:muted?'var(--pg-muted)':'var(--pg-ink)'},value);}
function line(s,x1,y1,x2,y2,color='var(--pg-edge)'){return add(s,'line',{x1,y1,x2,y2,stroke:color,'stroke-width':1.1});}
function tip(n,value){n.setAttribute('tabindex','0');n.setAttribute('aria-label',value);function show(){const t=$('tooltip'),r=n.getBoundingClientRect();t.textContent=value;t.hidden=false;t.style.left=Math.max(5,Math.min(innerWidth-305,r.left+8))+'px';t.style.top=Math.max(5,Math.min(innerHeight-t.offsetHeight-5,r.bottom+7))+'px';}n.addEventListener('mouseenter',show);n.addEventListener('focus',show);n.addEventListener('mouseleave',()=>{$('tooltip').hidden=true;});n.addEventListener('blur',()=>{$('tooltip').hidden=true;});}
function table(id,headers,rows,numeric=[]){const t=node('table'),thead=node('thead'),tr=node('tr');headers.forEach((v,i)=>{const th=node('th',v,numeric.includes(i)?'num':undefined);th.scope='col';tr.append(th);});thead.append(tr);t.append(thead);const body=node('tbody');for(const row of rows){const r=node('tr');row.forEach((v,i)=>{const td=node('td',undefined,numeric.includes(i)?'num':undefined);td.append(v instanceof Node?v:String(v));r.append(td);});body.append(r);}t.append(body);$(id).replaceChildren(t);return t;}
function list(items){return items.length<2?items.join(''):items.slice(0,-1).join(', ')+' and '+items[items.length-1];}
function mb(bytes){return (bytes/1e6).toLocaleString('en-US',{minimumFractionDigits:1,maximumFractionDigits:1})+' MB';}

// Model identity is read from the registry name, e.g. "Qwen3.5-0.8B Q4_K_M"; anything after " · " is run metadata, not part of the model.
const identities={};
function identity(m){if(identities[m.key])return identities[m.key];
  const base=m.name.split(' · ')[0],cut=base.lastIndexOf(' '),model=base.slice(0,cut),quant=base.slice(cut+1);
  const size=(model.match(/-(\d+(?:\.\d+)?)B(?:-|$)/)||[])[1],bits=(quant.match(/^Q(\d+)/)||[])[1],omni=/omni/i.test(model);
  return identities[m.key]={model:omni?model+' (text only)':model,quant,quantLabel:bits?`${quant}, ${bits}-bit`:quant,
    params:size?(omni?`${size}, model class`:size):'Not published',date:dates[m.cohort].short,dateLong:dates[m.cohort].long};}
function showDates(){return $('cohort').value==='all';}
function short(m){const i=identity(m);return `${i.model} ${i.quant}`+(showDates()?` (${i.date})`:'');}
function full(m){const i=identity(m);return `${i.model} · ${i.quantLabel} · tested ${i.date}`;}
function lines(m){const i=identity(m);return [i.model,i.quantLabel+(showDates()?` · tested ${i.date}`:'')];}
function who(m){const i=identity(m),n=node('span',undefined,'who');n.append(node('strong',i.model),node('small',i.quantLabel+(showDates()?` · tested ${i.date}`:'')));return n;}
function runtimeName(cohort){const m=D.models.find(m=>m.cohort===cohort),b=m.build.split('\n')[0].replace(/^version:\s*/,'');return /^b\d/.test(b)?`llama.cpp ${b}`:`runtime ${b}`;}

function run(m){return m.runs[Number($('run').value)];}
// Ranked by measured core score; equal scores share a rank and are listed alphabetically.
function selected(){return D.models.filter(m=>showDates()||m.cohort===$('cohort').value).sort((a,b)=>run(b).core_passed-run(a).core_passed||full(a).localeCompare(full(b)));}
function rankOf(m,ms){const score=run(m).core_passed;return {rank:1+ms.filter(o=>run(o).core_passed>score).length,tied:ms.filter(o=>run(o).core_passed===score).length>1};}

// Horizontal chart: two-line model labels on the left, or above each bar on narrow screens.
function nice(v){const p=10**Math.floor(Math.log10(v)),f=v/p;return (f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*p;}
const marks={
  bar(s,r,x,y){const n=add(s,'rect',{x:x(0),y,width:Math.max(1.5,x(r.value)-x(0)),height:20,rx:1.5,fill:r.color||'var(--pg-blue)'});tip(n,`${r.tip}\n${r.display}`);label(s,x(r.value)+6,y+15,r.display,'start',11);},
  stack(s,r,x,y){let at=0;for(const seg of r.segments){if(!seg.value)continue;const n=add(s,'rect',{x:x(at),y,width:Math.max(1,x(at+seg.value)-x(at)-1.5),height:20,fill:seg.color});tip(n,`${r.tip}\n${seg.label}: ${seg.value} of ${seg.total}`);at+=seg.value;}label(s,x(at)+6,y+15,r.display,'start',11);},
  pair(s,r,x,y){r.pairs.forEach((p,j)=>{const top=y+j*13,n=add(s,'rect',{x:x(0),y:top,width:Math.max(1.5,x(p.value)-x(0)),height:10,rx:1,fill:p.color});tip(n,`${r.tip}\n${p.label}: ${p.display}`);label(s,x(p.value)+6,top+9,`${p.label} ${p.display}`,'start',10);});},
  box(s,r,x,y,o){const d=r.box,c=y+10,col='var(--pg-blue)';line(s,x(d.min),c,x(d.max),c,col);[d.min,d.max].forEach(v=>line(s,x(v),c-6,x(v),c+6,col));const n=add(s,'rect',{x:x(d.q1),y:c-9,width:Math.max(2,x(d.q3)-x(d.q1)),height:18,fill:'var(--pg-card)',stroke:col});line(s,x(d.median),c-9,x(d.median),c+9,'var(--pg-ink)').setAttribute('stroke-width',2.2);tip(n,`${r.tip}\n${d.n} calls\nfastest ${d.min.toFixed(3)} s · slowest ${d.max.toFixed(3)} s\nmiddle half ${d.q1.toFixed(3)}–${d.q3.toFixed(3)} s\nmedian ${d.median.toFixed(3)} s`);label(s,x(o.max)+6,c+4,d.median.toFixed(2)+' s','start',11);}
};
function draw(box,rows,o){
  const w=Math.max(300,box.clientWidth||680),narrow=w<560,left=narrow?0:Math.min(210,Math.round(w*.36)),right=o.right||76,pw=w-left-right;
  const tall=o.kind==='pair'?6:0,rh=(narrow?60:46)+tall,axis=24,max=typeof o.max==='function'?o.max(rows):o.max,ticks=o.ticks?o.ticks(max):[0,max/2,max];
  let h=6;const ys=rows.map(r=>{const y=h;h+=r.heading?32:rh;return y;});h+=axis;
  const s=svg('svg',{width:w,height:h,viewBox:`0 0 ${w} ${h}`,role:'img','aria-label':box.closest('figure').querySelector('h3').textContent});box.append(s);
  const x=v=>left+Math.max(0,v)/max*pw;
  for(const t of ticks){line(s,x(t),4,x(t),h-axis+2);label(s,x(t),h-7,o.tick?o.tick(t):String(t),x(t)<24?'start':'middle',11,true);}
  rows.forEach((r,i)=>{const y=ys[i];
    if(r.heading){label(s,0,y+22,r.heading,'start',12).setAttribute('font-weight','700');return;}
    label(s,0,y+(narrow?14:17),r.lines[0],'start',12).setAttribute('font-weight','650');label(s,0,y+(narrow?28:32),r.lines[1],'start',11,true);
    marks[o.kind](s,r,x,narrow?y+34:y+9,{...o,max});});
}
// Timing charts draw each test date with its own axis, because the runtime builds differ.
function plot(id,build,o){const box=$(id);box.replaceChildren();const ms=selected();
  const groups=o.byDate&&showDates()?Object.keys(dates).map(c=>[c,ms.filter(m=>m.cohort===c)]).filter(g=>g[1].length):[[null,ms]];
  for(const [c,group] of groups){let target=box;if(c){target=node('div',undefined,'subchart');target.append(node('h4',`Tested ${dates[c].long} · ${runtimeName(c)}`));box.append(target);}draw(target,build(group),o);}}
function rowFor(m,extra){return {lines:lines(m),tip:full(m),...extra};}

function showTab(id){active=id;document.querySelectorAll('.panel').forEach(s=>s.hidden=s.id!==id);document.querySelectorAll('nav button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===id)));$('tooltip').hidden=true;render();}

function overview(){const ms=selected();
  $('overview-title').textContent='Results on 32 core questions';
  $('overview-lede').textContent='20 document questions, 8 off-topic requests and 4 tests of missing, conflicting or misleading evidence.'+(ms.every(m=>run(m).core_passed<32)?' No model shown passed all 32.':'');
  const legend=$('core-legend');legend.replaceChildren();for(const k of ['book','scope','handling']){const s=node('span'),i=node('i');i.style.background=kinds[k].color;s.append(i,`${kinds[k].name} (${D.cases.filter(c=>c.kind===k).length})`);legend.append(s);}
  plot('core-score',group=>group.map(m=>rowFor(m,{display:`${run(m).core_passed}/32`,segments:['book','scope','handling'].map(k=>({value:run(m).groups[k].passed,total:run(m).groups[k].total,label:kinds[k].name,color:kinds[k].color}))})),{kind:'stack',max:32,ticks:()=>[0,8,16,24,32]});
  table('scorecard',['Rank','Model and quantization','Core score','From the document','Off-topic refused','Tricky inputs','Median answer time','Parameters (billions)','File size'],ms.map(m=>{const r=run(m),i=identity(m),k=rankOf(m,ms),rank=node('span',String(k.rank),'rank');if(k.tied)rank.append(node('small','tied'));const total=node('strong',`${r.core_passed}/32`);
    return [rank,who(m),total,`${r.groups.book.passed}/20`,`${r.groups.scope.passed}/8`,`${r.groups.handling.passed}/4`,r.latency.core.median.toFixed(2)+' s',i.params,mb(m.profile.bytes)];}),[2,3,4,5,6,7,8]);
  $('scorecard-note').textContent=`Ranked by core score in Run ${Number($('run').value)+1}. Equal scores share a rank and are listed alphabetically. Median answer time covers the 32 core questions on one Apple M3 Pro laptop`+(showDates()?'; compare times only between configurations tested on the same date.':'.');
  const notes=[],ul=$('overview-notes');
  for(const m of ms.filter(m=>run(m).thinking_markers))notes.push(`${short(m)} wrote “thinking” markers such as </think> in ${run(m).thinking_markers} of 40 answers in this run, even though thinking was switched off. The raw text is kept and scored as written.`);
  const cut=ms.filter(m=>run(m).length_cutoffs).sort((a,b)=>run(b).length_cutoffs-run(a).length_cutoffs);
  if(cut.length)notes.push(`Answers cut off at the 192-token output limit, out of 40 in this run: ${list(cut.map(m=>`${short(m)} ${run(m).length_cutoffs}`))}. Cut-off answers are scored as returned.`);
  if(ms.some(m=>/omni/i.test(m.name)))notes.push('LFM3-Omni-2B was tested with text input and text output only. Its speech and vision abilities were not loaded or evaluated.');
  const sameScores=ms.every(m=>m.runs.every(r=>r.core_passed===m.runs[0].core_passed)),diff=ms.filter(m=>m.same_answers<40);
  notes.push((sameScores?'Run 1 and Run 2 gave the same scores for every configuration shown. ':'')+(diff.length?`Answer text was identical between runs for all 40 questions, except ${list(diff.map(m=>`${short(m)} (${m.same_answers} of 40)`))}.`:'Answer text was identical between runs for all 40 questions.')+' Repeats check consistency; they are not extra independent questions.');
  notes.push('These results cover one booklet, one prompt and fixed settings. A high score here is a useful signal, not proof of reliability on other documents, subjects or devices.');
  ul.replaceChildren(...notes.map(n=>node('li',n)));}

function core(){const ms=selected();
  plot('category-bars',group=>['book','scope','handling'].flatMap(k=>{const total=run(group[0]).groups[k].total;return [{heading:`${kinds[k].name} · out of ${total}`},...group.map(m=>{const c=run(m).groups[k];return rowFor(m,{value:c.passed/c.total*100,display:`${c.passed}/${c.total}`,color:kinds[k].color,tip:`${full(m)}\n${kinds[k].name}`});})];}),{kind:'bar',max:100,ticks:()=>[0,50,100],tick:v=>v+'%'});
  const t=node('table',undefined,'matrix'),thead=node('thead'),head=node('tr');head.append(node('th','Question'));for(const m of ms){const th=node('th'),i=identity(m);th.scope='col';th.append(i.model,node('small',i.quant+(showDates()?` · ${i.date}`:'')));head.append(th);}thead.append(head);t.append(thead);
  const body=node('tbody');for(const k of ['book','scope','handling']){const g=node('tr',undefined,'group'),th=node('th',kinds[k].name);th.colSpan=ms.length+1;th.scope='colgroup';g.append(th);body.append(g);
    for(const c of D.cases.filter(c=>c.split==='core'&&c.kind===k)){const row=node('tr');row.append(node('td',c.short));for(const m of ms){const td=node('td'),a=run(m).answers[c.id],b=node('button',a.task_success?'✓':'×','cell');b.dataset.pass=a.task_success;b.setAttribute('aria-label',`${c.question} ${full(m)}: ${a.task_success?'passed':'failed'}. Open the exact answer.`);b.onclick=()=>openAnswer(m.key,c.id);td.append(b);row.append(td);}body.append(row);}}
  t.append(body);$('matrix').replaceChildren(t);
  const states=['correct','incorrect_or_incomplete','unanswered','unverified_detail'];
  plot('factual-bars',group=>group.map(m=>rowFor(m,{display:`${run(m).book_factual.correct||0}/20`,segments:states.map((s,j)=>({value:run(m).book_factual[s]||0,total:20,label:factualNames[s],color:factualColors[j]}))})),{kind:'stack',max:20,ticks:()=>[0,5,10,15,20]});
  table('factual-table',['Model',...states.map(s=>factualNames[s])],ms.map(m=>[who(m),...states.map(s=>run(m).book_factual[s]||0)]),[1,2,3,4]);
  plot('citation-bars',group=>group.map(m=>rowFor(m,{value:run(m).book_citation_presence,display:`${run(m).book_citation_presence}/20`})),{kind:'bar',max:20,ticks:()=>[0,10,20]});}

function runtime(){const ms=selected(),split=$('timingSplit').value,within=c=>split==='all'||c.split===split;
  plot('size-bars',group=>group.map(m=>rowFor(m,{value:m.profile.bytes/1e6,display:mb(m.profile.bytes)})),{kind:'bar',right:86,max:rows=>nice(Math.max(...rows.map(r=>r.value))),tick:v=>v.toLocaleString('en-US')+' MB'});
  plot('latency-boxes',group=>group.map(m=>rowFor(m,{box:run(m).latency[split]})),{kind:'box',byDate:true,right:62,max:rows=>nice(Math.max(...rows.map(r=>r.box.max))),tick:v=>Number(v.toFixed(2))+' s'});
  plot('length-bars',group=>group.map(m=>rowFor(m,{value:run(m).median_output_tokens[split],display:`${run(m).median_output_tokens[split]} tokens`})),{kind:'bar',right:84,max:rows=>nice(Math.max(50,...rows.map(r=>r.value))),tick:v=>String(Math.round(v))});
  plot('repeat-bars',group=>group.map(m=>rowFor(m,{pairs:m.runs.map((r,i)=>({label:`Run ${i+1}`,value:r.latency[split].median,display:r.latency[split].median.toFixed(2)+' s',color:i?'var(--pg-gold)':'var(--pg-blue)'}))})),{kind:'pair',byDate:true,right:92,max:rows=>nice(Math.max(...rows.flatMap(r=>r.pairs.map(p=>p.value)))),tick:v=>Number(v.toFixed(2))+' s'});
  table('runtime-table',['Model','Parameters (billions)','File size','Calls','Median time','Middle half of times','Median output tokens','Cut off at 192 tokens','Thinking markers'],ms.map(m=>{const d=run(m).latency[split],a=D.cases.filter(within).map(c=>run(m).answers[c.id]);
    return [who(m),identity(m).params,mb(m.profile.bytes),d.n,d.median.toFixed(3)+' s',`${d.q1.toFixed(3)}–${d.q3.toFixed(3)} s`,run(m).median_output_tokens[split],a.filter(a=>a.finish_reason==='length').length,a.filter(a=>a.thinking_marker).length];}),[1,2,3,4,5,6,7,8]);
  $('runtime-table').append(node('p','“Cut off” counts answers that reached the 192-token output limit. “Thinking markers” counts answers containing an explicit opening or closing think tag, or a non-empty reasoning field, despite thinking being switched off; no marker does not prove the answer contains no reasoning-style text. Counts follow the selected questions and run.'+(showDates()?' Times compare only within one test date.':''),'caption'));}

function supplement(){const ms=selected();
  plot('knowledge-bars',group=>group.map(m=>rowFor(m,{value:run(m).groups.knowledge.passed,display:`${run(m).groups.knowledge.passed}/8`})),{kind:'bar',max:8,ticks:()=>[0,4,8]});
  plot('disclosure-bars',group=>group.map(m=>rowFor(m,{value:run(m).knowledge_disclosure,display:`${run(m).knowledge_disclosure}/8`,color:'var(--pg-olive)'})),{kind:'bar',max:8,ticks:()=>[0,4,8]});
  table('supplement-table',['Model','Correct','Wrong or incomplete','Not answered','Adds unverified detail','Honest about source'],ms.map(m=>{const r=run(m),f=r.knowledge_factual;return [who(m),`${r.groups.knowledge.passed}/8`,f.incorrect_or_incomplete||0,f.unanswered||0,f.unverified_detail||0,`${r.knowledge_disclosure}/8`];}),[1,2,3,4,5]);}

function options(select,values,current){select.replaceChildren();values.forEach(([key,title])=>{const o=node('option',title);o.value=key;select.append(o);});if(values.some(v=>v[0]===current))select.value=current;}
function questions(){const current=$('question').value,g=$('group').value,q=$('search').value.toLowerCase();const cases=D.cases.filter(c=>(g==='all'||c.kind===g||c.split===g)&&c.question.toLowerCase().includes(q));options($('question'),cases.map(c=>[c.id,c.question]),current);evidence();}
function openAnswer(key,id){$('model').value=key;$('group').value='all';$('search').value='';questions();$('question').value=id;showTab('evidence');}
function evidence(){const box=$('answer-detail');box.replaceChildren();const c=D.cases.find(c=>c.id===$('question').value),m=D.models.find(m=>m.key===$('model').value);if(!c||!m){box.append(node('p','No questions match this search.'));return;}
  const a=run(m).answers[c.id];box.append(node('p',`${c.split==='core'?'Core question':'Beyond the booklet, scored separately'} · ${kinds[c.kind].name}`,'eyebrow'),node('h3',c.question),node('p',`${a.task_success?'✓ Passed':'× Failed'} · ${full(m)} · Run ${Number($('run').value)+1}`,'outcome'+(a.task_success?'':' fail')));
  box.append(node('p','Expected: '+c.expected,'expected'),node('p','Exact answer','eyebrow'),node('div',a.content,'answer'));
  if(a.note)box.append(node('p','Reviewer’s note: '+a.note));
  if(a.thinking_marker)box.append(node('p','This answer contains an explicit thinking marker, even though thinking was switched off. The raw text is shown and scored as written.','outcome fail'));
  box.append(node('p',`Fact check: ${factualNames[a.factual_status]}. ${a.provenance_pass===null?'':`Honest about source: ${a.provenance_pass?'yes':'no'}. `}${a.seconds.toFixed(3)} s · ${a.output_tokens} output tokens · ${a.finish_reason==='length'?'cut off at the 192-token limit':'finished normally'}`,'detailsline'));
  const context=node('details');context.append(node('summary','The exact five passages the model received'));
  c.passages.forEach((id,i)=>{const p=D.passages[id],part=node('div',undefined,'passage');if(p.synthetic){part.append(node('p',`[P${i+1}] Test passage written for this question; not in the booklet`,'synthetic'));}else{const a=node('a',`[P${i+1}] Booklet PDF, page ${p.pdf_page}`);a.href=D.source.source_url+'#page='+p.pdf_page;a.target='_blank';a.rel='noopener';part.append(a);}part.append(node('p',p.text));context.append(part);});box.append(context);
  const hash=node('details');hash.append(node('summary','Input fingerprint and source checks'),node('p','SHA-256 of the exact messages sent: '+c.prompt_sha256,'detailsline'));
  if(c.expected_pages.length)hash.append(node('p','Booklet pages expected to contain the answer: '+c.expected_pages.join(', ')+'. Retrieving the right page is a proxy; it does not prove every passage supports the answer.'));
  if(c.kind==='knowledge'){hash.append(node('p','A search of the full booklet confirmed it does not define this. The reference below was used only by the reviewer, not given to the model.'));const refs=D.external.references;const refkey={class_d:'classes',class_k:'classes',co2_action:'co2',thermal_runaway:'thermal',stop_drop_roll:'roll'}[c.id]||c.id;if(refs[refkey]){const a=node('a','Open the reviewer’s reference');a.href=refs[refkey];a.target='_blank';a.rel='noopener';hash.append(a);}}
  box.append(hash);}

function method(){const mode=$('cohort').value,mixed=mode==='all',cohort=D.cohorts['2026-10-28-compatible-runtime'],ms=selected();
  table('model-table',['Model','Parameters (billions)','Quantization','File','Tested','Runtime','Input and output'],ms.map(m=>{const i=identity(m),f=node('span'),a=node('a',m.profile.filename);a.href=m.download_url;a.target='_blank';a.rel='noopener';f.append(a,node('span',`${m.profile.bytes.toLocaleString('en-US')} bytes · SHA-256 ${m.profile.sha256}`,'hash'));f.lastChild.style.display='block';
    return [node('strong',i.model),i.params,i.quantLabel,f,i.dateLong,runtimeName(m.cohort),m.evaluation_mode?'Text only; vision projector and audio codec not loaded':'Text'];}),[1]);
  const thinking=ms.filter(m=>m.runs.some(r=>r.thinking_markers));
  table('method-table',['Setting','Recorded value'],[['Context window','4,096 tokens including up to 192 output tokens'],['Request','Temperature 0; answer returned in one piece, not streamed; no tools'],['Runtime',mixed?'Two builds: see the table above. Compare timings only within one test date.':mode===cohort.id?cohort.runtime_version:runtimeName(mode)],['Server controls','4 CPU threads; 1 request at a time; Metal offload with 99 GPU layers; no vision projector for text-only tests'],['Sampling controls','top-k 20; top-p 0.95; min-p 0; repeat penalty 1'],['Order',mixed?'See each test date’s own order.':ms.slice().sort((a,b)=>D.models.indexOf(a)-D.models.indexOf(b)).map(short).join(' → ')],['Runs','Two complete 40-question runs per configuration, each after an identical unscored warm-up'],['Thinking control','Switched off in the runtime and in the chat template.'+(thinking.length?' '+thinking.map(m=>`${short(m)} still wrote explicit thinking markers in ${m.runs.map(r=>r.thinking_markers).join(' and ')} of 40 answers (Run 1 and Run 2).`).join(' '):'')],['Question split','32 core and 8 beyond the booklet; chosen after the original data collection and kept unchanged'],['Scope of claims','One dataset and prompt; no speech or vision, other subjects, peak memory or on-device measurements']]);
  $('system-prompt').textContent=D.system_prompt;
  const b=$('source-detail');b.replaceChildren();const a=node('a',`${D.source.title} · ${D.source.publisher} · ${D.source.publication}`);a.href=D.source.source_url;a.target='_blank';a.rel='noopener';b.append(a,node('p','24 PDF pages, 25 indexed passages. PDF SHA-256: '+D.source.sha256+'.','detailsline'),node('p','Five passages were retrieved per question using a 384-dimensional MiniLM text encoder and SQLite full-text search, combined by reciprocal rank fusion with k = 60. For each of the 20 document questions, at least one expected booklet page is among the five passages. This shared retrieval check is not a comparison of retrieval methods.'),node('p','The conflict and planted-instruction tests replace only the fifth passage with clearly marked test text. The original top five passages are kept in dataset.json. Source spacing repairs and the terms used to confirm absences are included in the package.'));}

function render(){const ms=selected(),files=new Set(D.models.map(m=>m.profile.sha256)).size,models=new Set(D.models.map(m=>identity(m).model)).size;
  options($('model'),ms.map(m=>[m.key,`${identity(m).model} · ${identity(m).quantLabel}`+(showDates()?` · tested ${identity(m).date}`:'')]),$('model').value);
  $('version').textContent=D.version;$('footer-version').textContent=D.version;
  $('meta').textContent=`${D.cases.length} questions · ${D.models.length} tested configurations of ${models} models (${files} files) · ${D.models.reduce((n,m)=>n+m.runs.length*D.cases.length,0).toLocaleString('en-US')} recorded answers · tested 27–28 October 2026 on an Apple M3 Pro laptop`;
  $('selection').textContent=`${ms.length} configurations shown`;
  const mode=$('cohort').value;
  $('cohort-note').textContent=mode==='2026-10-28-compatible-runtime'?`Tested 28 October 2026 on ${runtimeName(mode)}. Qwen3.5-0.8B Q4_K_M is the same file as in the 27 October tests, re-run here so that answer times share one runtime build. Both LFM3 models were run with text input and output only.`:mode==='all'?'Both test dates. Scores use the same questions and grading, so they can be compared. Answer times cannot, because the runtime builds differ; timing charts are split by date. Qwen3.5-0.8B Q4_K_M appears twice, once per date.':`Tested 27 October 2026 on ${runtimeName(mode)}. All original answers and judgments are preserved unchanged.`;
  if(active==='overview')overview();if(active==='core')core();if(active==='runtime')runtime();if(active==='supplement')supplement();if(active==='method')method();if(active==='evidence')questions();}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>showTab(b.dataset.tab));['run','timingSplit','cohort'].forEach(id=>$(id).addEventListener('change',render));['model','question'].forEach(id=>$(id).addEventListener('change',evidence));$('group').addEventListener('change',questions);$('search').addEventListener('input',questions);
$('inspectSupplement').onclick=()=>{$('group').value='knowledge';$('search').value='';showTab('evidence');};
$('downloadScores').onclick=()=>{const data=D.models.map(m=>{const i=identity(m);return {configuration:m.key,model:i.model,parameters_billions:i.params,quantization:i.quant,file:m.profile.filename,bytes:m.profile.bytes,tested:i.dateLong,cohort:m.cohort,runtime:runtimeName(m.cohort),runs:m.runs.map(r=>({run:r.run,core_passed:r.core_passed,core_total:r.core_total,groups:r.groups,thinking_markers:r.thinking_markers,length_cutoffs:r.length_cutoffs}))};});const url=URL.createObjectURL(new Blob([JSON.stringify({benchmark:'PocketGround',version:D.version,models:data},null,2)],{type:'application/json'}));const a=node('a');a.href=url;a.download='pocketground-scorecard.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
let timer,lastWidth=innerWidth;window.addEventListener('resize',()=>{if(innerWidth===lastWidth)return;lastWidth=innerWidth;clearTimeout(timer);timer=setTimeout(render,120);});render();
