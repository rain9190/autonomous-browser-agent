"""Fixed read-only form observation and native Playwright actions. No model code."""
import hashlib
import json
from playwright.sync_api import expect

GROUPS='[data-field]'  # controlled practice form
GOOGLE_GROUPS='[role="listitem"]'
READ=r'''groups => groups.filter(g=>{const r=g.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(g).visibility!=='hidden'}).map((g,i)=>{
 const native=!!g.closest('[data-practice]');
 const title=(native?g.querySelector('legend,label[data-title]'):g.querySelector('.M7eMe,[role="heading"]'));
 const label=(title?title.innerText:g.getAttribute('aria-label')||'').replace(/\s*\*\s*$/,'').trim();
 const req=native?g.dataset.required==='true':!!g.querySelector('.vnumgf,[aria-required="true"]');
 const visible=e=>e.getClientRects().length && getComputedStyle(e).visibility!=='hidden';
 const text=[...g.querySelectorAll('input:not([type=hidden]):not([type=radio]):not([type=checkbox]):not([type=submit]):not([type=button]),textarea')].filter(visible);
 const radio=[...g.querySelectorAll(native?'input[type=radio]':'[role=radio]')].filter(visible);
 const boxes=[...g.querySelectorAll(native?'input[type=checkbox]':'[role=checkbox]')].filter(visible);
 const select=g.querySelector(native?'select':'[role=listbox]');
 const optionLabel=e=>native?(e.closest('label')?.innerText||e.getAttribute('aria-label')||e.value).trim():(e.getAttribute('data-value')||e.getAttribute('aria-label')||e.innerText).trim();
 let kind='unsupported',options=[],value=null;
 if(select){kind='select';options=[...select.querySelectorAll(native?'option':'[role=option]')].map(e=>(e.innerText||e.getAttribute('data-value')||'').trim()).filter(Boolean);
 value=native?(select.selectedOptions[0]?.textContent||'').trim():(select.querySelector('[aria-selected=true]')?.innerText||select.innerText||'').trim();}
 else if(radio.length){kind='radio';options=radio.map(optionLabel);value=radio.filter(e=>native?e.checked:e.getAttribute('aria-checked')==='true').map(optionLabel);}
 else if(boxes.length){kind='checkbox';options=boxes.map(optionLabel);value=boxes.filter(e=>native?e.checked:e.getAttribute('aria-checked')==='true').map(optionLabel);}
 else if(text.length===1 && ['text','email','tel','url','number',''].includes(text[0].type||'')){kind='text';value=text[0].value;}
 else if(text.length===1 && text[0].tagName==='TEXTAREA'){kind='text';value=text[0].value;}
 if(Array.isArray(value)&&value.some(v=>['__other_option__','Other','Other:'].includes(v)))kind='unsupported';
 if(g.querySelector('[role=grid]') || g.querySelectorAll('[role=radiogroup]').length>1)kind='unsupported';
 if(kind==='select'&&(!options.length||options.includes('Choose')))options=options.filter(x=>x!=='Choose');
 const err=[...g.querySelectorAll('[role=alert],.RHiWt')].filter(visible).map(e=>e.innerText.trim()).filter(Boolean);
 if(native)for(const e of text)if(e.value&&e.validity&&!e.validity.valid)err.push(e.validationMessage);
 return {field_id:'q'+i,label,required:req,kind,options,value,errors:err};
}).filter(x=>x.label)'''


def group_selector(page):return GROUPS if page.locator('[data-practice]').count() else GOOGLE_GROUPS


def observe(page):
    selector=group_selector(page)
    raw=page.locator(selector).evaluate_all(READ)
    if len(raw)>40:raise ValueError('Too many questions')
    for f in raw:
        if len(f['label'])>600 or len(f['options'])>30 or any(len(o)>500 for o in f['options']):raise ValueError('Question observation too large')
        if len(set(f['options']))!=len(f['options']):f['kind']='unsupported'
    # Use actual DOM positions, not filtered-list positions, for target locators.
    # READ keeps IDs before removing titleless groups; locate by the visible sequence.
    signature=hashlib.sha256(json.dumps([(f['field_id'],f['label'],f['kind'],f['options']) for f in raw],sort_keys=True).encode()).hexdigest()
    next_buttons=page.get_by_role('button',name='Next',exact=True)
    can_next=any(next_buttons.nth(i).is_visible() for i in range(next_buttons.count()))
    submit=page.get_by_role('button',name='Submit',exact=True)
    at_end=any(submit.nth(i).is_visible() for i in range(submit.count()))
    if not raw:raise ValueError('No supported form questions found; the form may require sign-in or be closed')
    return {'fields':raw,'signature':signature,'has_next':can_next,'at_end':at_end}


def group(page,field):
    groups=page.locator(group_selector(page));visible=[groups.nth(i) for i in range(groups.count()) if groups.nth(i).is_visible()]
    return visible[int(field['field_id'][1:])]


def apply(page,field,answer):
    fresh=observe(page)
    match=next((f for f in fresh['fields'] if f['field_id']==field['field_id'] and f['label']==field['label'] and f['kind']==field['kind']),None)
    if match is None:raise ValueError('Form changed; re-observe')
    g=group(page,field);native=group_selector(page)==GROUPS
    if field['kind']=='text':
        loc=g.locator('input:not([type=hidden]),textarea')
        loc=next(loc.nth(i) for i in range(loc.count()) if loc.nth(i).is_visible())
        loc.fill(answer.text,timeout=5000)
    elif field['kind']=='select':
        if native:g.locator('select').select_option(label=answer.choices[0],timeout=5000)
        else:
            g.get_by_role('listbox').click(timeout=5000)
            g.get_by_role('option',name=answer.choices[0],exact=True).click(timeout=5000)
    else:
        opts=g.locator(('input[type=radio]' if field['kind']=='radio' else 'input[type=checkbox]') if native else ('[role=radio]' if field['kind']=='radio' else '[role=checkbox]'))
        for i,label in enumerate(field['options']):
            loc=opts.nth(i);wanted=label in answer.choices
            if field['kind']=='radio' and not wanted:continue
            if native:loc.set_checked(wanted,timeout=5000)
            else:
                current=loc.get_attribute('aria-checked')=='true'
                if current!=wanted:loc.click(timeout=5000)
    actual=next(f for f in observe(page)['fields'] if f['field_id']==field['field_id'])
    if not matches(actual,answer):raise ValueError('Field read-back did not match')


def matches(field,answer):
    if field['kind']=='text':return field['value']==answer.text
    if field['kind']=='select':return field['value']==answer.choices[0]
    return set(field['value'] or [])==set(answer.choices)


def populated(field):
    v=field['value']
    return bool(v) and v not in ('Choose','Choose an option') and not field['errors']


def next_section(page,signature):
    button=page.get_by_role('button',name='Next',exact=True)
    button=next(button.nth(i) for i in range(button.count()) if button.nth(i).is_visible())
    button.click(timeout=5000)
    # No Submit tool exists. Never choose navigation by approximate button text.
    page.wait_for_timeout(350)
    if observe(page)['signature']==signature:raise ValueError('Next did not advance; check required fields')


def operation_cost(field,answer):
    if matches(field,answer):return 0
    if field['kind']=='select':return 2  # conservative for native; custom dropdown opens then chooses
    if field['kind']=='checkbox':return len(set(field['value'] or []) ^ set(answer.choices))
    return 1
