from urllib.parse import urlsplit, unquote
import re

MAX_CALLS=24
MAX_ACTIONS=60
MAX_SECTIONS=8
MAX_FIELDS=40


def validate_url(value,practice_origin=None):
    if value=='practice' and practice_origin:
        return practice_origin+'/practice'
    if not isinstance(value,str) or len(value)>2048:raise ValueError('Invalid form link')
    try:p=urlsplit(value)
    except ValueError:raise ValueError('Invalid form link')
    if p.username or p.password or p.fragment:raise ValueError('Use a direct responder link')
    if practice_origin and value==practice_origin+'/practice':return value
    if p.scheme!='https' or p.port not in (None,443):raise ValueError('Use a public Google Forms link')
    if p.hostname=='forms.gle' and re.fullmatch(r'/[A-Za-z0-9_-]+',p.path):return value
    if p.hostname=='docs.google.com' and re.fullmatch(r'/forms/(?:d/e|d)/[A-Za-z0-9_-]+/viewform',p.path):return value
    raise ValueError('Use a Google Forms responder link ending in viewform')


def navigation_allowed(url,practice_origin):
    try:validate_url(url,practice_origin);return True
    except ValueError:return False


def request_allowed(url,method,navigation,practice_origin):
    p=urlsplit(url)
    if url.startswith(practice_origin+'/practice'):
        return p.netloc==urlsplit(practice_origin).netloc and method in ('GET','HEAD') and p.path in ('/practice','/practice.js')
    if p.scheme!='https':return False
    if navigation:return method in ('GET','HEAD') and navigation_allowed(url,practice_origin)
    # No final response submission. Some form configurations may require this endpoint
    # even for progression; stop explicitly rather than weaken the review-first rule.
    if p.hostname=='docs.google.com':
        if re.search(r'/(formResponse|submit)(?:/|$)',unquote(p.path),re.I):return False
        return method in ('GET','HEAD') or (method=='POST' and p.path.endswith('/draftresponse'))
    return method in ('GET','HEAD') and (p.hostname=='www.gstatic.com' or
        p.hostname=='fonts.gstatic.com' or p.hostname=='fonts.googleapis.com' or
        (p.hostname or '').endswith('.googleusercontent.com'))


def request_body(body,origin):
    if not isinstance(body,dict) or set(body)!={'url','instruction'}:raise ValueError('Enter a form link and your instructions')
    text=body['instruction']
    if not isinstance(text,str) or not 3<=len(text.strip())<=6000:raise ValueError('Add your instructions and details (up to 6,000 characters)')
    return {'url':validate_url(body['url'],origin),'instruction':text.strip(),'practice_origin':origin}
