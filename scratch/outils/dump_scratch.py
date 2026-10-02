import json,sys
p=json.load(open(sys.argv[1]))
def inp(blocks,v):
    if v is None: return 'null'
    kind=v[0]
    if kind==1:
        x=v[1]
        if isinstance(x,list): return repr(x[1])
        return render(blocks,x) if x else 'null'
    if kind in (2,3):
        x=v[1]
        if isinstance(x,list):
            if x[0] in (12,13): return '('+x[1]+')'
            return repr(x[1])
        return render(blocks,x)
    return repr(v)
def render(blocks,bid):
    b=blocks.get(bid)
    if b is None: return '?'
    if isinstance(b,list): return repr(b)
    s=b['opcode']
    parts=[]
    for k,v in b.get('fields',{}).items(): parts.append(f'{k}={v[0]!r}')
    for k,v in b.get('inputs',{}).items():
        if k in ('SUBSTACK','SUBSTACK2'): continue
        parts.append(f'{k}={inp(blocks,v)}')
    return s+'('+', '.join(parts)+')'
def stack(blocks,bid,ind,out):
    while bid:
        b=blocks[bid]
        out.append('  '*ind+render(blocks,bid)+f'   #{bid}')
        for sk in ('SUBSTACK','SUBSTACK2'):
            if sk in b.get('inputs',{}):
                v=b['inputs'][sk]
                sub=v[1] if isinstance(v[1],str) else None
                out.append('  '*ind+('} else {' if sk=='SUBSTACK2' else '{'))
                if sub: stack(blocks,sub,ind+1,out)
                if sk=='SUBSTACK2': out.append('  '*ind+'}')
                elif 'SUBSTACK2' not in b['inputs']: out.append('  '*ind+'}')
        bid=b.get('next')
for t in p['targets']:
    out=[f'######## {t["name"]}']
    bl=t['blocks']
    for bid,b in bl.items():
        if isinstance(b,dict) and b.get('topLevel') and b['opcode']!='procedures_prototype':
            out.append('')
            stack(bl,bid,0,out)
    open(sys.argv[2]+'/'+t['name'].replace(' ','_')+'.txt','w').write('\n'.join(out))
