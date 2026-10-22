'use strict';
chrome.action.onClicked.addListener(async tab => {
  if (!tab.id || !tab.url) return;
  const opening=chrome.sidePanel.open({windowId:tab.windowId});
  await chrome.storage.session.set({target: {id:tab.id, origin:new URL(tab.url).origin, title:tab.title||''}});
  await opening;
});
const allowed = new Set(['begin','observe','apply','next','stop']);
chrome.runtime.onMessage.addListener((message,sender,reply) => {
  if (sender.id !== chrome.runtime.id || sender.url !== chrome.runtime.getURL('panel.html') || message?.type!=='command') return;
  (async()=>{
    const {target}=await chrome.storage.session.get('target');
    if (!target || message.tabId!==target.id || !allowed.has(message.command?.op)) throw Error('Open the assistant from the form tab.');
    const tab=await chrome.tabs.get(target.id);
    const url=new URL(tab.url);
    if (url.origin!==target.origin || !['https:','http:'].includes(url.protocol)) throw Error('The page changed. Open the assistant again.');
    if (message.command.op!=='stop') {
      const active=await chrome.tabs.query({active:true,windowId:tab.windowId});
      if (active[0]?.id!==target.id) throw Error('Return to the form tab before filling.');
    }
    // Packaged code only, isolated from the website. No model-provided JavaScript.
    await chrome.scripting.executeScript({target:{tabId:target.id},files:['content.js']});
    return await chrome.tabs.sendMessage(target.id,{type:'form-assistant',command:message.command});
  })().then(reply).catch(()=>reply({error:'The form tab is unavailable or changed. Open the assistant from that tab again.'}));
  return true;
});

globalThis.__formAssistantBackgroundReady=true;
