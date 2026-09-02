#!/usr/bin/env python3
"""Generate preview.svg with live GitHub stats. Used by GitHub Actions."""

import json, html as h, os, sys, urllib.request, urllib.error
from collections import Counter

USERNAME = "RuckieOfficial"
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

import time

def gh_get(url, retries=3):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-readme-bot")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 202:   # GitHub warming cache
                    time.sleep(3); continue
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 202:
                time.sleep(3); continue
            print(f"  warn HTTP {e.code}: {url}", file=sys.stderr); return None
        except Exception as e:
            print(f"  warn: {e}", file=sys.stderr); return None
    return None

def fetch_stats():
    print("Fetching GitHub stats…")
    user  = gh_get(f"https://api.github.com/users/{USERNAME}") or {}
    repos = gh_get(f"https://api.github.com/users/{USERNAME}/repos?per_page=100") or []
    public_repos = user.get("public_repos", 0)
    followers    = user.get("followers", 0)
    stars = sum(r.get("stargazers_count", 0) for r in repos if isinstance(r, dict))
    commits = 0
    for r in repos:
        if not isinstance(r, dict): continue
        s = gh_get(f"https://api.github.com/repos/{USERNAME}/{r['name']}/stats/commit_activity")
        if s and isinstance(s, list):
            commits += sum(w.get("total", 0) for w in s)
    if commits == 0:            # fallback if all repos returned 202
        commits = -1            # signal: use "735+" display
    print(f"  repos={public_repos} stars={stars} followers={followers} commits≈{commits}")
    return dict(repos=public_repos, stars=stars, followers=followers, commits=commits)

# ── Palette ────────────────────────────────────────────────────────────────────
BG='#060606'; BORDER='#1a1a1a'; BORDER2='#2a2a2a'
O1='#ffb454'; O2='#ff9933'; O3='#cc7a00'; OSOFT='#e8921a'; CREAM='#ffe0a0'
W1='#e5e5e5'; W2='#bbbbbb'; G1='#888888'; G2='#555555'; G3='#333333'
FONT='Consolas,monospace'

# ── Layout ─────────────────────────────────────────────────────────────────────
CW,CH=2.8,5.6; COLS,ROWS=180,90
ASCII_W=int(CW*COLS); ASCII_H=int(CH*ROWS)
TERM_W=430; GAP=14; PAD=18; HDR_H=66
TW=PAD+ASCII_W+GAP+TERM_W+PAD; TH=PAD+HDR_H+10+ASCII_H+PAD
fs=round(CH*0.88,1); cy=PAD+HDR_H+10; ax=PAD; tx=PAD+ASCII_W+GAP
TFS=10.5; TLH=14.5; TP=12; TF=FONT

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(SCRIPT_DIR,"gitascii.json"),encoding="utf-8") as f:
    data=json.load(f)
ascii_rows=[]; ascii_colors=[]
for w in data.get("widgets",[]):
    if w.get("widgetId")=="ascii-art":
        ascii_rows=w["config"].get("asciiText",[]); ascii_colors=w["config"].get("asciiColors",[])

def q(c,s=32): r,g,b=int(c[1:3],16),int(c[3:5],16),int(c[5:7],16); return f'#{min(round(r/s)*s,255):02x}{min(round(g/s)*s,255):02x}{min(round(b/s)*s,255):02x}'
qc=[[q(c) for c in row] for row in ascii_colors]
uc=Counter(c for row in qc for c in row)
ci={col:f'c{i}' for i,col in enumerate(sorted(uc))}

def tt(text,col,ay,fs2=TFS,bold=False,x=None):
    xx=x if x is not None else tx+TP; fw=' font-weight="bold"' if bold else ''
    return f'<text x="{xx}" y="{ay}" font-family="{TF}" font-size="{fs2}"{fw} fill="{col}">{h.escape(str(text))}</text>'
def div(label,ay):
    lx=tx+TP; rx=tx+TERM_W-TP; mid=ay-5; lw=len(label)*6.1+8
    return (f'<line x1="{lx}" y1="{mid}" x2="{rx}" y2="{mid}" stroke="{G2}"/>'
            f'<rect x="{lx}" y="{mid-8}" width="{lw:.0f}" height="11" fill="{BG}"/>'
            +tt(label,O1,ay,bold=True))
def ir(label,val,ay,lcol=O2,vcol=W1,d=1):
    lp=f' {label}:'; dp=' '+'·'*d+' '
    x0=tx+TP+6; x1=x0+len(lp)*6.1; x2=x1+len(dp)*6.1
    return tt('·',G1,ay,x=tx+TP)+tt(lp,lcol,ay,x=x0)+tt(dp,G2,ay,x=x1)+tt(str(val),vcol,ay,x=x2)
def tag_row(items,ay):
    x=tx+TP+10; r=''
    for txt,col in items: r+=tt(f'[{txt}]',col,ay,x=x); x+=len(txt)*6.1+16
    return r
def skill_bar(label,pct,ay,col=O1):
    BX=tx+TP+200; BW=180; fw=int(BW*pct/100); ew=BW-fw
    return (tt('·',G1,ay,x=tx+TP)+tt(f' {label}',O2,ay,x=tx+TP+8)
            +f'<rect x="{BX}" y="{ay-9}" width="{fw}" height="9" fill="{col}" rx="1"/>'
            +f'<rect x="{BX+fw}" y="{ay-9}" width="{ew}" height="9" fill="{G3}" rx="1"/>'
            +tt(f'{pct}%',G1,ay,x=BX+BW+6))
def stat_badge(label,val,ay,x):
    full = f'· {label}:'          # počítáme celý řetězec včetně '· '
    lw   = len(full) * 6.1
    return tt(full,O2,ay,x=x) + tt(f'{val}',W1,ay,x=x+lw+6)

def build_svg(stats):
    commits_str = f"{stats['commits']:,}" if stats['commits']>0 else "735+"
    css='<style>'+''.join(f'.{cls}{{fill:{col}}}' for col,cls in ci.items())+'</style>'
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{TW}" height="{TH}">',css,
         f'<rect width="{TW}" height="{TH}" fill="{BG}"/>']
    # Header
    hx,hy=PAD,PAD
    out+=[f'<line x1="{hx}" y1="{hy+HDR_H}" x2="{TW-PAD}" y2="{hy+HDR_H}" stroke="{BORDER2}"/>',
          tt('Lukáš Rücker',W1,hy+32,fs2=26,bold=True,x=hx),
          tt(f'@{USERNAME}',O1,hy+54,fs2=11,x=hx+2),
          tt('Senior Full-Stack Developer  ·  Creative Technologist  ·  Embedded Systems',G1,hy+54,fs2=11,x=hx+130)]
    # ASCII
    out+=[f'<rect x="{ax}" y="{cy}" width="{ASCII_W}" height="{ASCII_H}" fill="{BG}" stroke="{BORDER}"/>',
          f'<g font-family="{FONT}" font-size="{fs}">']
    for ri in range(min(ROWS,len(ascii_rows))):
        rtxt=ascii_rows[ri]; rcol=qc[ri] if ri<len(qc) else []
        yp=round(cy+ri*CH+fs,1); i=0
        while i<min(COLS,len(rtxt),len(rcol)):
            col=rcol[i]; cls=ci[col]; j=i+1
            while j<min(COLS,len(rtxt),len(rcol)) and qc[ri][j]==col: j+=1
            seg=rtxt[i:j]
            if seg.strip():
                out.append(f'<text x="{round(ax+i*CW,1)}" y="{yp}" class="{cls}" textLength="{round(len(seg)*CW,1)}" lengthAdjust="spacingAndGlyphs">{h.escape(seg)}</text>')
            i=j
    out.append('</g>')
    # Terminal
    out+=[f'<rect x="{tx}" y="{cy}" width="{TERM_W}" height="{ASCII_H}" fill="{BG}" stroke="{BORDER}"/>',
          f'<clipPath id="tp"><rect x="{tx}" y="{cy}" width="{TERM_W}" height="{ASCII_H}"/></clipPath>',
          '<g clip-path="url(#tp)">']
    y=cy+TP+TLH+2
    # Identity
    out.append(div('RuckieOfficial@github',y)); y+=TLH+3
    out.append(ir('Role','Senior Full-Stack Dev & Creative Technologist',y,vcol=CREAM)); y+=TLH
    out.append(ir('Location','Czech Republic',y)); y+=TLH
    out.append(ir('Experience','8+ years',y,vcol=O1)); y+=TLH
    out.append(ir('Focus','Web · Embedded · UI/UX · 3D',y,vcol=W2)); y+=TLH+4
    # Tech Stack
    out.append(div('Tech Stack',y)); y+=TLH+3
    out.append(tt(' Languages:',O2,y,x=tx+TP+6)); y+=TLH
    out.append(tag_row([('TypeScript',CREAM),('C#',O1),('Python',W2),('Rust',OSOFT),('JS',O3)],y)); y+=TLH
    out.append(tt(' Frontend:',O2,y,x=tx+TP+6)); y+=TLH
    out.append(tag_row([('React',O1),('Three.js',CREAM),('R3F',OSOFT),('Vite',W2),('MUI',O3),('Framer',W2)],y)); y+=TLH
    out.append(tt(' Backend / Infra:',O2,y,x=tx+TP+6)); y+=TLH
    out.append(tag_row([('Docker',O1),('REST',W2),('.NET',OSOFT),('Node.js',W2),('Git',G1)],y)); y+=TLH
    out.append(tt(' Embedded:',O2,y,x=tx+TP+6)); y+=TLH
    out.append(tag_row([('Rust',OSOFT),('ESP32',O3),('no_std',G1),('GIF codec',W2)],y)); y+=TLH+4
    # Creative Skills
    out.append(div('Creative Skills',y)); y+=TLH+3
    out.append(skill_bar('3D / WebGL',    90,y,O1));   y+=TLH+1
    out.append(skill_bar('UI/UX & Design',88,y,OSOFT));y+=TLH+1
    out.append(skill_bar('Motion & Video',82,y,O3));   y+=TLH+1
    out.append(skill_bar('Digital Art',   78,y,W2));   y+=TLH+4
    # Projects
    out.append(div('Notable Projects',y)); y+=TLH+3
    out.append(ir('Pragis','B2B orders portal · React + TypeScript',y,vcol=CREAM)); y+=TLH
    out.append(ir('Placek','B2B e-commerce platform · custom design',y,vcol=W2)); y+=TLH
    out.append(ir('rusty-nano-frame','★4  Fast GIF on ESP32 · Rust',y,vcol=OSOFT)); y+=TLH
    out.append(ir('ruckie.cz','3D interactive WebGL portfolio',y,vcol=O1)); y+=TLH+4
    # Contact & Live Stats
    out.append(div('Contact & Stats',y)); y+=TLH+3
    out.append(ir('Web','https://ruckie.cz',y,vcol=O1)); y+=TLH
    # Dynamic badges
    badge_data=[('Repos',stats['repos']),('Stars',stats['stars']),
                ('Commits',commits_str),('Followers',stats['followers'])]
    
    total_w = 0
    widths = []
    for label, val in badge_data:
        w = len(f'· {label}:') * 6.1 + 6 + len(str(val)) * 6.1
        widths.append(w)
        total_w += w
        
    gap = ((TERM_W - TP*2) - total_w) / (len(badge_data) - 1)
    cx = tx + TP
    for i, (label, val) in enumerate(badge_data):
        out.append(stat_badge(label,val,y,cx))
        cx += widths[i] + gap
    out+=['</g>','</svg>']
    return ''.join(out)

if __name__=='__main__':
    stats=fetch_stats()
    svg=build_svg(stats)
    out_path=os.path.join(SCRIPT_DIR,'preview.svg')
    with open(out_path,'w',encoding='utf-8') as f: f.write(svg)
    print(f"Saved {out_path}  ({len(svg)/1024:.1f} KB)")
