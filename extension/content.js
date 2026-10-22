/* Fixed DOM adapter. Injected only into the user-authorised main frame. */
(()=>{
'use strict';
if(globalThis.__formAssistantInstalled)return;
globalThis.__formAssistantInstalled=true;
let run=null, scope=null, signature='', entries=new Map(), busy=false, navigation=[];
const guardedDocs=new Set();
const protectedText=/\b(pay|payment|password|api key|verification code|one.time code|credit card|bank account|passport|aadhaar|social security|tax id|signature|agree|consent|certify|declaration|terms|authorize|authorise)\b/i;
const visible=e=>!!e && e.getClientRects().length>0 && e.ownerDocument.defaultView.getComputedStyle(e).visibility!=='hidden' && !e.closest('[hidden],[inert]');
const clean=s=>(s||'').replace(/\s+/g,' ').replace(/\s*\*\s*$/,'').trim();
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const guardSubmit=e=>{if(run){e.preventDefault();e.stopImmediatePropagation();}};
const check=id=>{if(!run || run!==id)throw Error('Run stopped.');};
const labelFor=e=>{
 const ids=(e.getAttribute('aria-labelledby')||'').split(/\s+/).filter(Boolean),root=e.getRootNode();
 return clean(ids.map(id=>root.getElementById?.(id)?.textContent||e.ownerDocument.getElementById(id)?.textContent||'').join(' ') || e.getAttribute('aria-label') ||
   [...(e.labels||[])].map(x=>x.textContent).join(' ') || e.getAttribute('placeholder') || e.getAttribute('data-placeholder') || e.getAttribute('title') || '');
};
const optionLabel=e=>clean(e.getAttribute('data-value')||e.getAttribute('aria-label')||labelFor(e)||e.textContent||e.value);
function chooseScope(){return {root:document};}
function rootsOnPage(){
 const result=[],seen=new Set();let elements=0;
 function visit(root){
  if(seen.has(root))return;seen.add(root);
  if(result.length>=16)throw Error('This page has too many embedded regions.');
  result.push(root);
  if(root.nodeType===9&&run){root.addEventListener('submit',guardSubmit,true);guardedDocs.add(root);}
  const nodes=[...root.querySelectorAll('*')];elements+=nodes.length;
  if(elements>16000)throw Error('This page is too large to inspect in one run.');
  for(const el of nodes){
   if(el.shadowRoot&&visible(el))visit(el.shadowRoot);
   if(el.tagName==='IFRAME'&&visible(el)){
    // Cross-origin/sandboxed frames remain inaccessible under browser permissions.
    try{if(el.contentDocument?.documentElement)visit(el.contentDocument);}catch{}
   }
  }
 }
 visit(document);return result;
}
function collect(){
 if(!scope)scope=chooseScope();
 const roots=rootsOnPage(),fields=[],owned=new Set();entries=new Map();let googleCount=0;
 const add=(el,label,kind,controls,options,value,required,errors=[])=>{
   if(!label)return;
   if(fields.length>=40)throw Error('This page has more than 40 visible fields.');
   if(label.length>600 || options.length>30 || options.some(x=>x.length>500))throw Error('This field is too large.');
   if(options.length!==new Set(options).size||options.some(x=>!x))kind='unsupported';
   if(Array.isArray(value)&&value.some(x=>['Other','Other:','__other_option__'].includes(x)))kind='unsupported';
   if(controls.some(x=>x.disabled||x.readOnly||x.getAttribute('aria-disabled')==='true'||x.getAttribute('aria-readonly')==='true'))kind='unsupported';
   if(protectedText.test(label)||controls.some(x=>/^(password|file|hidden)$/.test(x.type||'')||/^(cc-|one-time-code|current-password|new-password)/i.test(x.autocomplete||''))){kind='unsupported';value=null;}
   if(typeof value==='string'&&value.length>2000)throw Error('An existing answer is too long.');
   const f={field_id:'q'+fields.length,label,kind,options,value,required,errors};
   fields.push(f);entries.set(f.field_id,{field:f,el,controls});
 };
 for(const root of roots){
  // Keep the Google question adapter, then also inspect controls outside its groups.
  for(const g of [...root.querySelectorAll('[role=listitem]')].filter(visible)){
   const title=g.querySelector('.M7eMe');if(!title)continue;
   const label=clean(title.textContent);
   const radios=[...g.querySelectorAll('[role=radio]')].filter(visible);
   const boxes=[...g.querySelectorAll('[role=checkbox]')].filter(visible);
   const selects=[...g.querySelectorAll('[role=listbox]')].filter(visible);
   const texts=[...g.querySelectorAll('input:not([type=hidden]):not([type=radio]):not([type=checkbox]),textarea')].filter(visible);
   let kind='unsupported',controls=[],options=[],value=null;
   if(selects.length===1){kind='select';controls=selects;options=[...selects[0].querySelectorAll('[role=option]')].map(optionLabel).filter(x=>x&&x!=='Choose');value=clean(selects[0].querySelector('[aria-selected=true]')?.textContent||selects[0].textContent);}
   else if(radios.length||boxes.length){kind=radios.length?'radio':'checkbox';controls=radios.length?radios:boxes;options=controls.map(optionLabel);value=controls.filter(x=>x.getAttribute('aria-checked')==='true').map(optionLabel);}
   else if(texts.length===1){controls=texts;kind=/^(text|email|tel|url|number|search|textarea)$/.test(texts[0].type||'text')?'text':'unsupported';if(kind==='text')value=texts[0].value;}
   if(g.querySelector('[role=grid]')||g.querySelectorAll('[role=radiogroup]').length>1)kind='unsupported';
   add(g,label,kind,controls,options,value,!!g.querySelector('.vnumgf,[aria-required=true]'),[...g.querySelectorAll('[role=alert],.RHiWt')].filter(visible).map(e=>clean(e.textContent)).filter(Boolean));
   googleCount++;
   g.querySelectorAll('input,textarea,select,[contenteditable],[role=textbox],[role=searchbox]').forEach(e=>owned.add(e));
  }
  const done=new Set();
  for(const el of [...root.querySelectorAll('input,textarea,select,[contenteditable],[role=textbox],[role=searchbox]')].filter(visible)){
   if(owned.has(el)||done.has(el)||/^(hidden|submit|button|reset|image)$/.test(el.type||''))continue;
   const native=['INPUT','TEXTAREA','SELECT'].includes(el.tagName);
   if(!native && (el.parentElement?.isContentEditable||el.querySelector('input,textarea,select,[contenteditable=true]')))continue;
   if(!native && !el.isContentEditable && !['textbox','searchbox'].includes(el.getAttribute('role')))continue;
   const fallback=clean(el.getAttribute('name')||el.id||'').replace(/([a-z])([A-Z])/g,'$1 $2').replace(/[_-]/g,' ');
   const label=labelFor(el)||fallback||'Text box '+(fields.length+1);
   const required=!!el.required||el.getAttribute('aria-required')==='true';
   if(/^(checkbox|radio)$/.test(el.type)){
    const fs=el.closest('fieldset'), name=el.name;
    const controls=[...root.querySelectorAll('input')].filter(x=>visible(x)&&x.type===el.type&&x.form===el.form&&
      (fs?x.closest('fieldset')===fs&&(!name||x.name===name):(name?x.name===name:x===el)));
    controls.forEach(x=>done.add(x));
    const groupLabel=clean(fs?.querySelector('legend')?.textContent|| (controls.length===1?label:el.getAttribute('data-question')||name))||label;
    const errors=controls.filter(x=>x.required&&!x.validity.valid).map(x=>x.validationMessage);
    add(fs||el,groupLabel,el.type,controls,controls.map(x=>labelFor(x)||clean(x.value)),controls.filter(x=>x.checked).map(x=>labelFor(x)||clean(x.value)),controls.some(x=>x.required),errors);
   }else if(el.tagName==='SELECT'){
    const options=[...el.options].filter(x=>!x.disabled&&x.value!=='').map(x=>clean(x.textContent));
    add(el,label,el.multiple?'unsupported':'select',[el],options,clean(el.selectedOptions[0]?.textContent),required);
   }else{
    const editable=!native&&el.isContentEditable;
    const kind=(editable||/^(text|email|tel|url|number|search|textarea)$/.test(el.type||''))?'text':'unsupported';
    const value=kind==='text'?(editable?el.innerText:el.value):null;
    add(el,label,kind,[el],[],value,required,el.value&&el.validity&&!el.validity.valid?[el.validationMessage]:[]);
   }
  }
 }
 if(!fields.length)throw Error(document.querySelector('iframe')?'This embedded page is not accessible to the extension.':'No visible editable fields found.');
 navigation=roots.flatMap(root=>[...root.querySelectorAll('button,[role=button],input[type=button],input[type=submit]')]).filter(e=>visible(e)&&/^next$/i.test(clean(e.textContent||e.value)));
 const owners=[...entries.values()].map(e=>e.el.closest('form'));
 const oneForm=owners.length&&owners[0]&&owners.every(f=>f===owners[0]);
 const canAdvance=!!oneForm||googleCount===fields.length;
 const has_next=navigation.length===1&&canAdvance;
 signature=JSON.stringify(fields.map(f=>[f.field_id,f.label,f.kind,f.options]));
 return {fields,signature,has_next,at_end:navigation.length===0};
}
function fingerprint(f){return JSON.stringify([f.field_id,f.label,f.kind,f.options]);}
function currentMatch(f,a){
 if(f.kind==='text')return f.value===a.text;
 if(f.kind==='select')return f.value===a.choices[0];
 return JSON.stringify([...(f.value||[])].sort())===JSON.stringify([...a.choices].sort());
}
function nativeValue(el,value){
 const win=el.ownerDocument.defaultView;
 if(el.isContentEditable){el.innerText=value;}else{
  const proto=el.tagName==='TEXTAREA'?win.HTMLTextAreaElement.prototype:win.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto,'value').set.call(el,value);
 }
 el.dispatchEvent(new win.Event('input',{bubbles:true,composed:true}));el.dispatchEvent(new win.Event('change',{bubbles:true,composed:true}));
}
async function apply(c){
 check(c.run_id);const fresh=collect();const entry=entries.get(c.field?.field_id);
 if(!entry||fingerprint(entry.field)!==fingerprint(c.field))throw Error('The question changed.');
 const f=entry.field,a=c.answer;
 if(!a||a.field_id!==f.field_id||a.status!=='fill'||f.kind==='unsupported'||protectedText.test(f.label))throw Error('Unsupported field action.');
 if(f.kind==='text'){
  if(typeof a.text!=='string'||a.text.length>2000||a.choices.length)throw Error('Invalid text answer.');
 }else if(!Array.isArray(a.choices)||!a.choices.length||a.choices.some(x=>!f.options.includes(x)||['Other','Other:','__other_option__'].includes(x))||
   new Set(a.choices).size!==a.choices.length||(['radio','select'].includes(f.kind)&&a.choices.length!==1))throw Error('Invalid choice.');
 if(currentMatch(f,a))return {ok:true};
 if((Array.isArray(f.value)?f.value.length:(!!f.value&&!['Choose','Choose an option'].includes(f.value)))&&c.allow_replace!==true)throw Error('Existing answer needs permission.');
 const id=c.run_id;entry.el.scrollIntoView({block:'center',behavior:'instant'});await delay(120);check(id);
 if(f.kind==='text'){entry.controls[0].focus();nativeValue(entry.controls[0],a.text);entry.controls[0].blur();}
 else if(f.kind==='select'){
  const el=entry.controls[0];
  if(el.tagName==='SELECT'){
   const option=[...el.options].find(x=>clean(x.textContent)===a.choices[0]&&!x.disabled);if(!option)throw Error('Option changed.');
   Object.getOwnPropertyDescriptor(el.ownerDocument.defaultView.HTMLSelectElement.prototype,'value').set.call(el,option.value);
   el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
  }else{
   el.click();await delay(150);check(id);
   const options=[...el.querySelectorAll('[role=option]')].filter(x=>visible(x)&&optionLabel(x)===a.choices[0]);
   if(options.length!==1)throw Error('Dropdown option unavailable.');options[0].click();
  }
 }else{
  for(let i=0;i<entry.controls.length;i++){
   check(id);const el=entry.controls[i],wanted=a.choices.includes(f.options[i]);
   if(f.kind==='radio'&&!wanted)continue;
   const selected=el.tagName==='INPUT'?el.checked:el.getAttribute('aria-checked')==='true';
   if(selected!==wanted){el.click();await delay(100);}
  }
 }
 await delay(150);check(id);
 const actual=collect().fields.find(x=>x.field_id===f.field_id);
 if(!actual||!currentMatch(actual,a))throw Error('The answer could not be verified.');
 return {ok:true};
}
async function command(c){
 if(c.op==='stop'){run=null;for(const doc of guardedDocs)doc.removeEventListener('submit',guardSubmit,true);guardedDocs.clear();return {ok:true};}
 if(c.op==='begin'){
  run=c.run_id;scope=chooseScope();rootsOnPage();return {ok:true};
 }
 check(c.run_id);
 if(c.op==='observe')return collect();
 if(c.op==='apply')return apply(c);
 if(c.op==='next'){
  const before=collect();if(before.signature!==c.signature)throw Error('The section changed.');
  const buttons=navigation;
  if(!before.has_next)throw Error('This page needs manual navigation.');
  if(buttons.length!==1)throw Error('No unambiguous Next button.');
  const b=buttons[0];if((b.tagName==='BUTTON'&&b.type==='submit')||b.disabled||b.getAttribute('aria-disabled')==='true')throw Error('This Next button requires manual review.');
  check(c.run_id);b.click();await delay(450);check(c.run_id);scope=null;
  const after=collect();if(after.signature===before.signature)throw Error('Next did not advance.');return {ok:true};
 }
 throw Error('Unknown command.');
}
chrome.runtime.onMessage.addListener((m,sender,reply)=>{
 if(sender.id!==chrome.runtime.id||m?.type!=='form-assistant')return;
 if(m.command?.op==='stop'){command(m.command).then(reply);return true;}
 if(busy){reply({error:'A field action is already running.'});return;}
 busy=true;command(m.command).then(reply).catch(e=>reply({error:e.message||'Form action failed.'})).finally(()=>busy=false);
 return true;
});
})();
