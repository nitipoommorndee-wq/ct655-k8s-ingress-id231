#!/usr/bin/env python3
"""เรนเดอร์ output จริงใน ../outputs เป็นภาพหน้าต่าง Terminal (พื้นดำ) — ไฟล์ c* = ssh k8s-control, l* = ssh k8s-lb, m* = Mac (client ภายนอก)"""
import html, json, math, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHAR_W, LINE_H, PAD_X, PAD_Y, BAR_H = 7.2258, 15, 10, 6, 28
MAX_COLS = 160

SESS = {
    "c": dict(plain="nitipoom@k8s-control:~/id-231$ ",
              html='<b class="g">nitipoom@k8s-control</b>:<b class="b">~/id-231</b>$ ',
              title="nitipoom@k8s-control: ~/id-231 — ssh nitipoom@192.168.64.3"),
    "l": dict(plain="nitipoom@k8s-lb:~$ ",
              html='<b class="g">nitipoom@k8s-lb</b>:<b class="b">~</b>$ ',
              title="nitipoom@k8s-lb: ~ — ssh nitipoom@192.168.64.6"),
    "m": dict(plain="nitipoommorndee@Nitipooms-MacBook-Air ~ % ",
              html="nitipoommorndee@Nitipooms-MacBook-Air ~ % ",
              title="nitipoommorndee — -zsh"),
}


def parse(text):
    blocks = []
    for raw in text.replace("\r", "").splitlines():
        line = raw.rstrip().expandtabs(8)
        if line.startswith("$ "):
            blocks.append([line[2:], []])
        elif blocks:
            blocks[-1][1].append(line)
    for b in blocks:
        while b[1] and not b[1][-1].strip():
            b[1].pop()
    return blocks


def render(name, blocks, sess, cols=None):
    S = SESS[sess]
    logical = []
    for cmd, out in blocks:
        logical.append((S["plain"] + cmd, True))
        logical += [(o, False) for o in out]
    logical.append((S["plain"], True))
    longest = max(len(t) for t, _ in logical)
    cols = cols or min(MAX_COLS, max(80, longest + 1))
    rows = []
    for t, is_prompt in logical:
        segs = [t[i:i + cols] for i in range(0, max(len(t), 1), cols)] or [""]
        for k, seg in enumerate(segs):
            if is_prompt and k == 0:
                rows.append(S["html"] + html.escape(seg[len(S["plain"]):]))
            else:
                rows.append(html.escape(seg))
    rows[-1] += '<span class="cur">&nbsp;</span>'
    w = math.ceil(cols * CHAR_W) + 2 * PAD_X
    h = BAR_H + len(rows) * LINE_H + 2 * PAD_Y
    title = f"{S['title']} — {cols}×{len(rows)}"
    page = f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;background:transparent}}
.win{{width:{w}px;height:{h}px;border-radius:10px;overflow:hidden;background:#000;box-sizing:border-box;border:1px solid #4a4a4a}}
.bar{{height:{BAR_H}px;background:linear-gradient(#3c3c3c,#2e2e2e);border-bottom:1px solid #111;position:relative;box-sizing:border-box}}
.dots{{position:absolute;left:10px;top:8px;display:flex;gap:8px}}
.dots i{{width:12px;height:12px;border-radius:50%;display:block}}
.t{{text-align:center;font:13px -apple-system,'Helvetica Neue',sans-serif;color:#c8c8c8;line-height:{BAR_H}px;white-space:nowrap;overflow:hidden;padding:0 80px}}
pre{{margin:0;padding:{PAD_Y}px {PAD_X}px;font:12px/{LINE_H}px Menlo,monospace;color:#f0f0f0;white-space:pre}}
.g{{color:#5fd35f}} .b{{color:#6f9cff}} .cur{{background:#a0a0a0}}
</style><div class="win"><div class="bar"><div class="dots"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i>
<i style="background:#28c840"></i></div><div class="t">{html.escape(title)}</div></div><pre>{chr(10).join(rows)}</pre></div>"""
    hp = SHOTS / f"{name}.html"
    hp.write_text(page)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    "--default-background-color=00000000", f"--window-size={w},{h}",
                    f"--screenshot={SHOTS / (name + '.png')}", hp.as_uri()], capture_output=True, check=True, timeout=60)
    hp.unlink()
    return {"file": f"shots/{name}.png", "w": w, "h": h, "cols": cols, "rows": len(rows)}


index = {}
for f in sorted(OUT.glob("[clm][0-9]*.txt")):
    key = f.stem.split("-")[0]
    index[key] = render(f.stem, parse(f.read_text()), key[0])
(SHOTS / "index.json").write_text(json.dumps(index, indent=1))
print("\n".join(f"{k:5s} {v['file']}  {v['cols']}x{v['rows']}" for k, v in index.items()))
