"""Animated agent floor for the Vitalis demo.

Five avatars walk between desks as the pipeline stages play out; the
skeptic fires envelopes at the extractor while challenging. Pure canvas
+ emoji — no external assets, works offline.
"""
import json

_AGENTS = [
    ["ingest", "\U0001f4e5", "Ingest", "#4f8cff"],
    ["extractor", "\U0001f52c", "Extractor", "#34c77b"],
    ["skeptic", "\U0001f6e1️", "Skeptic", "#ff9f43"],
    ["counselor", "\U0001f4ac", "Counselor", "#22d3ee"],
    ["arbiter", "⚖️", "Arbiter", "#b06cff"],
]

# (seconds, caption, agents at desks, envelope routes)
_SCRIPT = [
    [1.6, "IngestAgent normalizes the report…",
     ["ingest"], []],
    [2.8, "MarkerExtractor pulls biomarkers…",
     ["ingest", "extractor"], [["ingest", "extractor"]]],
    [2.8, "RangeSkeptic validates every flag…",
     ["ingest", "extractor", "skeptic"],
     [["skeptic", "extractor"], ["extractor", "skeptic"]]],
    [2.0, "Counselor drafts plain-language summary…",
     ["ingest", "extractor", "skeptic", "counselor"],
     [["counselor", "arbiter"]]],
    [2.4, "Arbiter adjudicates — answer or abstain.",
     ["ingest", "extractor", "skeptic", "counselor", "arbiter"], []],
]

_JS = (
    "(function(){\n"
    "const cv=document.getElementById('vfloor'),cx=cv.getContext('2d');\n"
    "const W=cv.width,H=cv.height;\n"
    "const agents=AGENTS_JSON;\n"
    "const script=SCRIPT_JSON;\n"
    "const n=agents.length, gap=W/(n+1);\n"
    "const homeX=i=>gap*(i+1), deskY=112, homeY=300;\n"
    "let pos=agents.map((a,i)=>({x:homeX(i),y:homeY}));\n"
    "let stage=0,tStage=0,last=performance.now(),envT=0;\n"
    "const lerp=(a,b,t)=>a+(b-a)*t;\n"
    "function target(i){const id=agents[i][0];\n"
    " const at=script[stage][2].indexOf(id)>=0;\n"
    " return {x:homeX(i),y:at?deskY:homeY};}\n"
    "function desk(i){const x=homeX(i);\n"
    " cx.fillStyle='#2b2f3a';cx.beginPath();cx.roundRect(x-58,deskY-32,116,60,10);cx.fill();\n"
    " cx.fillStyle='#3a3f4d';cx.beginPath();cx.roundRect(x-58,deskY-32,116,18,10);cx.fill();\n"
    " cx.fillStyle='#9aa3b5';cx.font='11px sans-serif';cx.textAlign='center';\n"
    " cx.fillText(agents[i][2],x,deskY+36);}\n"
    "function agent(i,active){const p=pos[i],col=agents[i][3];\n"
    " if(active){const r=26+4*Math.sin(performance.now()/180);\n"
    "  cx.strokeStyle=col;cx.globalAlpha=.55;cx.lineWidth=3;\n"
    "  cx.beginPath();cx.arc(p.x,p.y,r,0,7);cx.stroke();cx.globalAlpha=1;}\n"
    " cx.fillStyle=col;cx.beginPath();cx.arc(p.x,p.y,20,0,7);cx.fill();\n"
    " cx.font='19px sans-serif';cx.textAlign='center';cx.textBaseline='middle';\n"
    " cx.fillText(agents[i][1],p.x,p.y+1);}\n"
    "function env(x0,y0,x1,y1,t){\n"
    " const x=lerp(x0,x1,t),y=lerp(y0,y1,t)-22*Math.sin(Math.PI*t);\n"
    " cx.font='16px sans-serif';cx.textAlign='center';cx.fillText('\\u2709\\ufe0f',x,y);}\n"
    "function frame(now){const dt=(now-last)/1000;last=now;tStage+=dt;envT+=dt;\n"
    " if(tStage>=script[stage][0]&&stage<script.length-1){stage++;tStage=0;}\n"
    " for(let i=0;i<n;i++){const tg=target(i),k=Math.min(1,dt*3.2);\n"
    "  pos[i].x=lerp(pos[i].x,tg.x,k);pos[i].y=lerp(pos[i].y,tg.y,k);}\n"
    " cx.clearRect(0,0,W,H);cx.fillStyle='#171a21';cx.fillRect(0,0,W,H);\n"
    " cx.strokeStyle='#262b36';cx.lineWidth=1;\n"
    " for(let y=40;y<H;y+=40){cx.beginPath();cx.moveTo(0,y);cx.lineTo(W,y);cx.stroke();}\n"
    " cx.fillStyle='#8b93a7';cx.font='13px sans-serif';cx.textAlign='left';\n"
    " cx.fillText('VITALIS \\u00b7 AGENT FLOOR',14,24);\n"
    " for(let i=0;i<n;i++)desk(i);\n"
    " const routes=script[stage][3];\n"
    " for(let k=0;k<routes.length;k++){\n"
    "  const a=agents.findIndex(a=>a[0]===routes[k][0]);\n"
    "  const b=agents.findIndex(a=>a[0]===routes[k][1]);\n"
    "  env(pos[a].x,pos[a].y,pos[b].x,pos[b].y,(envT*0.9+k*0.5)%1);}\n"
    " const act=script[stage][2];\n"
    " for(let i=0;i<n;i++)agent(i,act.indexOf(agents[i][0])>=0);\n"
    " cx.fillStyle='#cfd6e4';cx.font='14px sans-serif';cx.textAlign='center';\n"
    " cx.fillText(script[stage][1],W/2,H-14);\n"
    " requestAnimationFrame(frame);}\n"
    "requestAnimationFrame(frame);\n"
    "})();"
)


def render_floor() -> str:
    """Self-contained floor HTML for st.components.v1.html."""
    js = _JS.replace("AGENTS_JSON", json.dumps(_AGENTS))
    js = js.replace("SCRIPT_JSON", json.dumps(_SCRIPT))
    js = js.replace("</script>", "<\\/script>")
    return (
        '<canvas id="vfloor" width="880" height="350" '
        'style="width:100%;border-radius:12px;display:block"></canvas>'
        "<script>" + js + "</script>"
    )
