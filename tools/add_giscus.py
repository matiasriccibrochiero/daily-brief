#!/usr/bin/env python3
"""Add giscus feedback (reactions + comments via GitHub Discussions) to a Daily Brief HTML file.

Usage: add_giscus.py <file.html> <YYYY-MM-DD>
Idempotent: does nothing if the file already has the feedback block.
- Bottom card "How was today's brief?" -> term brief-<date> (lazy iframe)
- Each <article class="feat|story"> gets a collapsed <details> "Feedback on this story"
  -> term story-<date>-<slug>; giscus is injected only when the details is opened.
"""
import re, sys, html

REPO, REPO_ID = "matiasriccibrochiero/daily-brief", "R_kgDOVQx5Jg"
CAT, CAT_ID = "Announcements", "DIC_kwDOVQx5Js4DJrHP"
THEME = "transparent_dark"
MARK = "<!-- giscus-feedback -->"
STOP = set("a an the and or of to in on for with at by from as is are was were be its it this that after before into over out up how why what who new now s".split())

CSS = """
  /* feedback (giscus) */
  .fb{margin-top:16px;border-top:1px solid rgba(255,255,255,.06);padding-top:12px}
  .fb summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--t2);padding:6px 12px 6px 10px;border-radius:999px;background:var(--s2)}
  .fb summary::-webkit-details-marker{display:none}
  .fb summary svg{width:14px;height:14px;stroke:var(--t2);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .15s}
  .fb[open] summary svg{transform:rotate(90deg)}
  .fb summary:hover{color:#fff}
  .fb .gslot{margin-top:12px}
  .gslot{min-height:120px}
  .gslot iframe{width:100%;border:0}
  .fbcard{margin-top:32px;border-radius:28px;padding:24px 20px}
  .fbcard h3{font-size:24px;font-weight:800;letter-spacing:-.035em;line-height:1.15;margin:14px 0 6px}
  .fbcard .hint{font-size:14px;color:var(--t2);line-height:1.45;margin-bottom:16px}
"""

JS = """<script>
/* giscus loader: one embed at a time (client.js targets the first .giscus), per-iframe resizing */
(function(){
  var CFG={repo:"%(repo)s",repoId:"%(repo_id)s",category:"%(cat)s",categoryId:"%(cat_id)s",mapping:"specific",strict:"1",
    reactionsEnabled:"1",emitMetadata:"0",inputPosition:"top",theme:"%(theme)s",lang:"en",loading:"lazy"};
  var frames=[],heights=new Map(),queue=Promise.resolve();
  function kebab(k){return k.replace(/[A-Z]/g,function(c){return "-"+c.toLowerCase()})}
  window.addEventListener("message",function(e){
    if(e.origin!=="https://giscus.app")return;
    var d=e.data; if(!d||typeof d!=="object"||!d.giscus)return;
    var f=null; for(var i=0;i<frames.length;i++){if(frames[i].contentWindow===e.source){f=frames[i];break}}
    if(d.giscus.resizeHeight&&f){heights.set(f,d.giscus.resizeHeight);f.style.height=d.giscus.resizeHeight+"px"}
    var ks=Object.keys(d.giscus);
    if(ks.length===1&&ks[0]==="resizeHeight"){e.stopImmediatePropagation();return}
    setTimeout(function(){heights.forEach(function(h,fr){fr.style.height=h+"px"})},0);
  });
  function mount(slot){
    if(!slot||slot.getAttribute("data-mounted"))return; slot.setAttribute("data-mounted","1");
    queue=queue.then(function(){return new Promise(function(done){
      slot.classList.add("giscus");
      var s=document.createElement("script"); s.src="https://giscus.app/client.js"; s.async=true; s.crossOrigin="anonymous";
      for(var k in CFG)s.setAttribute("data-"+kebab(k),CFG[k]);
      s.setAttribute("data-term",slot.getAttribute("data-term"));
      s.onload=s.onerror=function(){var fr=slot.querySelector("iframe");if(fr)frames.push(fr);
        slot.classList.remove("giscus");slot.classList.add("gdone");done()};
      slot.parentNode.insertBefore(s,slot);
    })});
  }
  document.querySelectorAll("details.fb").forEach(function(d){
    d.addEventListener("toggle",function(){if(d.open)mount(d.querySelector(".gslot"))});
  });
  mount(document.getElementById("fb-brief"));
})();
</script>"""

CHEV = '<svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>'

def slugify(title, used):
    words = re.findall(r"[a-z0-9]+", html.unescape(re.sub(r"<[^>]+>", "", title)).lower())
    keep = [w for w in words if w not in STOP] or words
    s = "-".join(keep[:4])[:40].strip("-") or "story"
    base, n = s, 2
    while s in used:
        s = f"{base}-{n}"; n += 1
    used.add(s)
    return s

def main(path, date):
    src = open(path, encoding="utf-8").read()
    if MARK in src:
        print("already has giscus; skipping"); return
    used = set(); terms = []
    def repl(m):
        body = m.group(0)
        h3 = re.search(r"<h3>(.*?)</h3>", body, re.S)
        slug = slugify(h3.group(1) if h3 else "story", used)
        term = f"story-{date}-{slug}"; terms.append(term)
        block = (f'\n    <details class="fb"><summary>{CHEV}Feedback on this story</summary>'
                 f'<div class="gslot" id="fb-{slug}" data-term="{term}"></div></details>\n  ')
        return body[: -len("</article>")] + block + "</article>"
    src = re.sub(r'<article class="(?:feat|story)">.*?</article>', repl, src, flags=re.S)
    card = (f'{MARK}\n  <section class="card fbcard" id="feedback">\n    <span class="lbl">Feedback</span>\n'
            f'    <h3>How was today\'s brief?</h3>\n'
            f'    <p class="hint">React or leave a comment on format, depth, or topics. Feedback shapes what gets covered and how, never which side a story takes.</p>\n'
            f'    <div class="gslot" id="fb-brief" data-term="brief-{date}"></div>\n  </section>\n\n  ')
    assert "<footer>" in src and "</style>" in src and "</body>" in src
    src = src.replace("<footer>", card + "<footer>", 1)
    src = src.replace("</style>", CSS + "</style>", 1)
    js = JS % dict(repo=REPO, repo_id=REPO_ID, cat=CAT, cat_id=CAT_ID, theme=THEME)
    src = src.replace("</body>", js + "\n</body>", 1)
    open(path, "w", encoding="utf-8").write(src)
    print(f"brief-{date}"); print("\n".join(terms))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
