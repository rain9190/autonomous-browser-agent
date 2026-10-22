'use strict';
const $=id=>document.getElementById(id), API='http://127.0.0.1:8766';
let token='',target=null,session=null,running=false,polling=false,lastCommand='',question=null,connected=false,ending=false;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function status(text,kind=''){$('status').textContent=text;$('dot').className=kind;}
function controls(){
 $('fill').disabled=!connected||!target||running||$('details').value.trim().length<3;
 $('stop').disabled=!running;$('details').disabled=running;
}
async function api(path,body,keepalive=false){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5000);
 try{
  const r=await fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token,'X-Extension-ID':chrome.runtime.id},
   body:JSON.stringify(body),signal:controller.signal,cache:'no-store',keepalive});
  const data=await r.json();if(!r.ok)throw Error(data.error||'Connection failed');return data;
 }finally{clearTimeout(timer);}
}
async function browser(command){
 const result=await chrome.runtime.sendMessage({type:'command',tabId:target.id,command});
 if(!result||result.error)throw Error(result?.error||'The browser did not respond.');return result;
}
async function connect(){
 token=$('code').value.trim()||token;
 try{await api('/connect',{});connected=true;await chrome.storage.session.set({connection:token});$('code').value='';$('connection').hidden=true;status('Ready when you are');}
 catch(e){connected=false;$('connection').hidden=false;$('connection-message').textContent='Start the local service and check the connection code.';}
 controls();
}
function showQuestion(q){
 if(q?.id===question?.id)return;
 question=q;$('question').hidden=!q;if(!q)return;
 $('question-label').textContent=q.kind==='overwrite'?'Replace the existing answer for “'+q.label+'”?':q.label;
 $('options').textContent=q.kind==='overwrite'?'':q.options.join(' · ');
 $('answer').value='';$('answer').hidden=q.kind==='overwrite';$('answer-buttons').hidden=q.kind==='overwrite';$('overwrite-buttons').hidden=q.kind!=='overwrite';
 if(q.kind!=='overwrite')$('answer').focus();
}
async function answer(value){
 if(!question||!session)return;
 try{await api('/answer',{id:session,question_id:question.id,answer:value});showQuestion(null);}
 catch{status('That answer could not be sent. Try again.','error');}
}
async function cleanup(){
 try{if(target)await browser({op:'stop',run_id:session});}catch{}
 await chrome.storage.session.remove('run');
}
async function stop(){
 const id=session;running=false;controls();showQuestion(null);status('Stopped');
 // Cancel in the page first, so any waiting click sequence sees the stop immediately.
 await cleanup();if(id)try{await api('/stop',{id});}catch{}
 session=null;
}
async function poll(){
 if(polling)return;polling=true;
 try{
  while(session&&running){
   const id=session,s=await api('/state',{id});if(session!==id||!running)break;
   status(s.message,s.running?'working':s.error?'error':s.ready?'ready':'');showQuestion(s.question);
   if(s.command&&s.command.id!==lastCommand){
    lastCommand=s.command.id;
    let result;
    try{result=await browser(s.command);}catch{result={error:'The form page changed or is unavailable.'};}
    if(running&&session===id)await api('/respond',{id,command_id:s.command.id,result});
   }
   if(!s.running){
    running=false;controls();showQuestion(null);
    $('manual').replaceChildren(...s.manual.map(label=>{const li=document.createElement('li');li.textContent=label;return li;}));$('manual').hidden=!s.manual.length;
    await cleanup();session=null;break;
   }
   await sleep(180);
  }
 }catch{
  status('Connection lost. Filling stopped. Reconnect to try again.','error');connected=false;
  await stop();status('Connection lost — reconnect to continue.','error');$('connection').hidden=false;
 }finally{polling=false;controls();}
}
async function start(){
 if(!target||!connected||running)return;
 running=true;controls();$('manual').hidden=true;status('Reading the form','working');lastCommand='';showQuestion(null);
 try{
  // Start a read-only check before spending a model call.
  await browser({op:'begin',run_id:'preflight'});
  await browser({op:'observe',run_id:'preflight'});
  const s=await api('/start',{facts:$('details').value.trim(),origin:target.origin});session=s.id;
  await browser({op:'begin',run_id:session});
  await chrome.storage.session.set({run:{id:session,tabId:target.id}});poll();
 }catch(e){await stop();status(e.message||'This form is not supported yet.','error');}
}
$('fill').addEventListener('click',start);$('stop').addEventListener('click',stop);
$('connect').addEventListener('click',connect);$('settings').addEventListener('click',()=>{$('connection').hidden=!$('connection').hidden;});
$('details').addEventListener('input',controls);$('continue').addEventListener('click',()=>answer($('answer').value));
$('replace').addEventListener('click',()=>answer('Replace'));$('keep').addEventListener('click',()=>answer('Keep'));
chrome.storage.onChanged.addListener(async(changes,area)=>{
 if(area!=='session'||!changes.target)return;
 const next=changes.target.newValue;
 if(running&&next?.id!==target?.id)await stop();
 target=next;$('site').textContent=target?new URL(target.origin).hostname:'Open a form, then click the extension.';controls();
});
window.addEventListener('pagehide',()=>{
 ending=true;
 if(session){browser({op:'stop',run_id:session}).catch(()=>{});api('/stop',{id:session},true).catch(()=>{});}
});
(async()=>{
 const stored=await chrome.storage.session.get(['connection','target','run']);token=stored.connection||'';target=stored.target||null;
 $('site').textContent=target?new URL(target.origin).hostname:'Open a form, then click the extension.';
 if(token)await connect();else $('connection').hidden=false;
 if(stored.run){session=stored.run.id;running=true;controls();poll();}
 controls();
})();
