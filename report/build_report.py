#!/usr/bin/env python3
"""Build diagram.png, report.pdf and test.pdf from the real outputs in ../outputs and the screenshots in web/."""
import html, json, re, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
IDX = json.loads((HERE / "shots" / "index.json").read_text())
URLS = dict(l.split(" ", 1) for l in (HERE / "web" / "urls.txt").read_text().splitlines())
e = html.escape


def txt(key):
    return next(OUT.glob(f"{key}-*.txt")).read_text()


def rows(text, cmd):
    blk = [l for l in text.split("$ " + cmd, 1)[1].split("\n$ ", 1)[0].splitlines()[1:]]
    return [l.split() for l in blk if l.strip()]


# ---------------------------------------------------------------- real values
LB_IP = (OUT / "ips.txt").read_text().split("=")[1].strip()
nodes = {r[0]: r[5] for r in rows(txt("c01"), "kubectl get nodes -o wide")[1:]}
svc = {r[0].split("/")[1]: r[2] for r in rows(txt("c16"), "kubectl -n id-231 get svc,endpoints -o wide") if r[0].startswith("service/")}
ep = {r[0].split("/")[1]: r[1] for r in rows(txt("c16"), "kubectl -n id-231 get svc,endpoints -o wide") if r[0].startswith("endpoints/")}
ING_SVC = next(r for r in rows(txt("c11"), "kubectl -n ingress-nginx get pods,svc -o wide") if r[0] == "service/ingress-nginx-controller")
ING_POD = next(r for r in rows(txt("c11"), "kubectl -n ingress-nginx get pods,svc -o wide") if r[0].startswith("pod/ingress-nginx-controller"))
assert "80:30081/TCP" in ING_SVC[4]
UPS = re.findall(r"server (\S+:30081)", txt("l01"))
assert sorted(u.split(":")[0] for u in UPS) == sorted(nodes.values())
CLIENT_MAC = re.search(r"^(192\.168\.64\.1) -> ", txt("l10"), re.M).group(1)
for k in ("l04", "l05", "l06", "l07"):
    assert txt(k).count("\n200") >= 1, k
assert "edited from admin.id-231.com" in txt("l09") and "edited from admin.id-231.com" in txt("c21")
replicas = {r[0].split("/")[1]: r[1] for r in rows(txt("c15"), "kubectl -n id-231 get deployment,replicaset -o wide") if r[0].startswith("deployment")}

# ---------------------------------------------------------------- diagram
OR, BL, GR, GY, RD, PU = "#E8710A", "#2F64D0", "#2E9E5B", "#6B7280", "#C2410C", "#7B3FE4"
SANS, MONO = "Sarabun, sans-serif", "Menlo, monospace"
svg = []


def R(x, y, w, h, fill="#fff", stroke="#999", sw=1.5, rx=10, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def T(x, y, s, size=14, weight=400, fill="#1F2937", anchor="start", mono=False):
    svg.append(f'<text x="{x}" y="{y}" font-family="{MONO if mono else SANS}" font-size="{size}" font-weight="{weight}" '
               f'fill="{fill}" text-anchor="{anchor}" style="white-space:pre">{e(str(s))}</text>')


def L(d, c, w=3, dash=None, mk=None):
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#{mk})"' if mk else ""
    svg.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{w}"{ds}{m} stroke-linejoin="round"/>')


W, H = 1400, 1110
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
svg.append("<defs>" + "".join(
    f'<marker id="{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
    f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for n, c in [("ar", RD), ("ao", OR), ("ag", GY), ("ap", PU)]) + "</defs>")
R(0, 0, W, H, fill="#fff", stroke="none", rx=0)
T(40, 44, "สถาปัตยกรรมระบบ www.id-231.com / admin.id-231.com", 25, 700, "#111827")
T(40, 70, "Client → /etc/hosts → External LB :80 → NodePort :30081 → Ingress Controller → Service (ClusterIP) → Pod", 14, 400, GY)

# client
R(380, 92, 640, 100, fill="#F3F4F6", stroke="#9CA3AF", sw=2)
T(700, 120, "Client (Linux / MacBook)", 17, 700, "#374151", "middle")
T(700, 146, f"/etc/hosts   {LB_IP} www.id-231.com", 13, 400, "#374151", "middle", mono=True)
T(700, 166, f"             {LB_IP} admin.id-231.com", 13, 400, "#374151", "middle", mono=True)
L("M700,192 V236", RD, 4, mk="ar")
T(716, 220, "HTTP :80  (Host: www.id-231.com / admin.id-231.com)", 13, 600, RD)

# LB
R(250, 240, 900, 122, fill="#FFF4EC", stroke=RD, sw=2.5, rx=14)
T(272, 270, "External Load Balancer: k8s-lb", 19, 700, RD)
T(1128, 270, "NginX reverse proxy", 14, 600, GY, "end")
T(272, 298, f"IP {LB_IP}   listen 80   server_name www.id-231.com admin.id-231.com", 13.5, 400, "#374151", mono=True)
T(272, 322, "upstream k8s_ingress  " + "  ".join(UPS), 13.5, 400, "#374151", mono=True)
T(272, 346, "proxy_set_header Host $host   (round robin)", 13.5, 400, "#374151", mono=True)

# cluster
CY = 420
R(40, CY, 1320, 670, fill="#FAFBFF", stroke=BL, sw=2.2, rx=16)
names = ["k8s-control", "k8s-worker1", "k8s-worker2"]
for i, n in enumerate(names):
    x = 60 + i * 435
    R(x, CY + 24, 410, 58, fill="#fff", stroke=OR, sw=2.2, rx=8)
    T(x + 14, CY + 48, n + ("  (control-plane)" if i == 0 else "  (worker)"), 14, 700, "#374151")
    T(x + 14, CY + 70, f"NodePort {nodes[n]}:30081", 13, 400, "#111827", mono=True)
    sx = 520 + i * 180
    L(f"M{sx},362 C{sx},400 {x + 205},390 {x + 205},{CY + 20}", OR, 3, mk="ao")

# ingress controller
IY = CY + 124
for i in range(3):
    L(f"M{265 + i * 435},{CY + 82} L{700 + (i - 1) * 120},{IY - 4}", OR, 2.4, mk="ao")
R(250, IY, 900, 150, fill="#F5F0FF", stroke=PU, sw=2.5, rx=14)
T(272, IY + 30, "Ingress Controller: ingress-nginx  (namespace ingress-nginx)", 17, 700, PU)
T(272, IY + 56, f"Service ingress-nginx-controller  NodePort  {ING_SVC[2]}  80:30081", 13, 400, "#374151", mono=True)
T(272, IY + 80, "Ingress www-id-231    www.id-231.com   /about  /research  /api", 13, 400, "#374151", mono=True)
T(272, IY + 102, "Ingress admin-id-231  admin.id-231.com /       rewrite-target: /edit", 13, 400, "#374151", mono=True)
T(272, IY + 126, f"controller pod {ING_POD[5]} on {ING_POD[6]}   ingressClassName: nginx", 13, 400, GY, mono=True)

# apps
AY = IY + 230
apps = [("app-about", "nginx:1.25", "80", "www.id-231.com/about", GR, "ConfigMap: index.html, photo.jpg"),
        ("app-research", "python:3.12-alpine", "8080", "www.id-231.com/research", BL, "PVC research-pvc → /data"),
        ("app-api", "python:3.12-alpine", "8080", "www.id-231.com/api/<text>", OR, "ConfigMap: app.py")]
for i, (name, img, port, url, col, extra) in enumerate(apps):
    x = 60 + i * 435
    R(x, AY, 410, 230, fill="#fff", stroke=col, sw=2.4, rx=12)
    T(x + 16, AY + 30, name, 19, 700, col)
    T(x + 394, AY + 30, f"replicas {replicas[name]}", 13, 600, GY, "end")
    for j, s in enumerate([f"Service   ClusterIP {svc[name]}:80", f"targetPort {port}", f"image     {img}"]):
        T(x + 16, AY + 58 + j * 22, s, 12.5, 400, "#374151", mono=True)
    T(x + 16, AY + 130, extra, 13, 400, "#374151")
    R(x + 14, AY + 150, 382, 30, fill="#F3F4F6", stroke="#D1D5DB", sw=1, rx=6)
    T(x + 205, AY + 170, url, 12.5, 600, "#111827", "middle", mono=True)
    if name == "app-research":
        R(x + 14, AY + 188, 382, 30, fill="#F5F0FF", stroke=PU, sw=1.2, rx=6)
        T(x + 205, AY + 208, "admin.id-231.com  →  /edit", 12.5, 600, PU, "middle", mono=True)
    lab = {"app-about": "/about", "app-research": "/research", "app-api": "/api"}[name]
    sx = 560 + i * 140
    L(f"M{sx},{IY + 150} C{sx},{IY + 195} {x + 205},{IY + 185} {x + 205},{AY - 4}", col, 3, mk="ag")
    T(x + 193 if i == 0 else x + 217, AY - 14, lab, 13, 700, col, "end" if i == 0 else "start", mono=True)
L(f"M760,{IY + 150} C790,{IY + 200} 600,{IY + 210} 560,{AY - 4}", PU, 2.4, dash="6 5", mk="ap")
T(546, AY - 14, "admin → /edit", 12.5, 700, PU, "end", mono=True)
T(60, AY + 262, "K8s Cluster (kubeadm v1.31, Flannel)", 19, 700, BL)
T(60, AY + 288, "namespace id-231   ·   Pod network 10.244.0.0/16   ·   PV research-pv (hostPath /mnt/id-231-research on k8s-worker1)", 13.5, 600, "#3730A3")

svg.append("</svg>")
SVG = "\n".join(svg)

FONT_CSS = "".join(f"@font-face{{font-family:Sarabun;src:url('fonts/Sarabun-{n}.ttf');font-weight:{w};}}"
                   for n, w in [("Regular", 400), ("SemiBold", 600), ("Bold", 700)])
(HERE / "diagram.html").write_text(f"<!doctype html><meta charset=utf-8><style>{FONT_CSS}html,body{{margin:0}}</style>{SVG}")

# ---------------------------------------------------------------- report parts
FIG = [0]


def cap(text):
    FIG[0] += 1
    return f"<figcaption>ภาพที่ {FIG[0]} {text}</figcaption>"


def shot(key, caption, maxh=232):
    m = IDX[key]
    w_mm = min(178.0, m["w"] * 0.2377)
    size = f"width:{w_mm:.1f}mm" if w_mm * m["h"] / m["w"] <= maxh else f"height:{maxh}mm"
    return f'<figure class="shot"><img src="{m["file"]}" style="{size}">{cap(caption)}</figure>'


def web(key, caption, width=150):
    return (f'<figure class="web"><div class="browser" style="width:{width}mm"><div class="bbar"><i></i><i></i><i></i>'
            f'<span class="url">{e(URLS[key])}</span></div><img src="web/{key}.png"></div>{cap(caption)}</figure>')


def fig_diagram():
    return f'<figure class="diag">{SVG}{cap("สถาปัตยกรรมระบบ")}</figure>'


c = lambda s: f"<code>{e(str(s))}</code>"
CSS = f"""{FONT_CSS}
@page {{ size: A4; margin: 15mm 16mm 16mm 16mm; @bottom-right {{ content: counter(page); font: 10pt Sarabun; color:#666; }} }}
* {{ box-sizing: border-box; }}
body {{ font-family: Sarabun, sans-serif; font-size: 11.5pt; line-height: 1.55; color:#1f2328; margin:0; }}
h2 {{ font-size: 14.5pt; color:#123a7a; border-bottom: 1.5pt solid #c9d6ef; padding: 4pt 0 2pt; margin: 14pt 0 6pt; break-after: avoid; }}
h3 {{ font-size: 12.5pt; margin: 10pt 0 4pt; padding-top: 3pt; break-after: avoid; }}
p {{ margin: 3pt 0 6pt; padding-top: 2pt; break-inside: avoid; }}
ul {{ margin: 2pt 0 8pt; padding: 4pt 0 0 18pt; }} li {{ margin-bottom: 1pt; }}
code {{ font-family: Menlo, monospace; font-size: 9pt; background:#f1f3f6; padding: 0 2pt; border-radius: 2pt; white-space: nowrap; }}
.who-top {{ font-size: 12pt; font-weight: 600; margin: 0 0 10pt; padding: 4pt 0 6pt; border-bottom: 1pt solid #c9d6ef; }}
figure {{ margin: 4pt 0 10pt; text-align:center; break-inside: avoid; }}
.shot img {{ display:block; margin:0 auto; }}
figcaption {{ font-size: 9.5pt; color:#444; margin-top: 3pt; padding-top: 2pt; }}
.diag svg {{ width: 100%; height: auto; }}
.browser {{ margin: 0 auto; border: 0.8pt solid #9aa3af; border-radius: 6pt; overflow: hidden; }}
.browser img {{ display:block; width:100%; }}
.bbar {{ background:#e5e7eb; padding: 4pt 6pt; display:flex; align-items:center; gap:4pt; border-bottom: 0.8pt solid #9aa3af; }}
.bbar i {{ width:7pt; height:7pt; border-radius:50%; background:#9ca3af; display:block; }}
.url {{ flex:1; margin-left:6pt; background:#fff; border-radius: 8pt; padding: 1pt 8pt; font: 8.5pt Menlo, monospace; text-align:left; color:#111; }}
table {{ border-collapse: collapse; width: 100%; font-size: 10pt; margin: 4pt 0 10pt; break-inside: avoid; }}
th, td {{ border: 0.8pt solid #c8ced6; padding: 3pt 6pt; vertical-align: top; text-align:left; }}
thead th {{ background:#123a7a; color:#fff; }}
td code {{ font-size: 8.4pt; }}
"""
WHO = '<div class="who-top">นายนิติภูมิ มอญดี &nbsp; รหัสนักศึกษา 68130231</div>'
REPO = "https://github.com/nitipoommorndee-wq/ct655-k8s-ingress-id231"

REPORT = f"""<!doctype html><html lang="th"><head><meta charset="utf-8"><title>CT655 K8s Ingress id-231</title><style>{CSS}</style></head><body>
{WHO}
<p>รหัสนักศึกษา 3 ตัวท้ายคือ 231 จึงใช้ชื่อ <code>www.id-231.com</code> และ <code>admin.id-231.com</code> &nbsp; GitHub: <code>{REPO}</code></p>

<h2>1. ภาพรวมของระบบ</h2>
<p>ใช้ cluster เดิม 3 node และเครื่อง <code>k8s-lb</code> จากงานที่แล้ว งานนี้เพิ่ม Ingress Controller (ingress-nginx) เข้าไปใน cluster
เพื่อแยกเส้นทางตามชื่อ host และ path ไปยังแอป 3 ตัว คือ <code>app-about</code>, <code>app-research</code> และ <code>app-api</code>
แต่ละแอปมี Service แบบ ClusterIP ของตัวเอง ส่วนเครื่อง LB รับที่พอร์ต 80 แล้วส่งต่อไปที่ NodePort 30081 ของ Ingress Controller</p>
{fig_diagram()}
<table><thead><tr><th style="width:36%">URL</th><th style="width:20%">แอป</th><th>การทำงาน</th></tr></thead><tbody>
<tr><td>{c("www.id-231.com/about")}</td><td>app-about</td><td>แสดงรูป ชื่อ และรหัสนักศึกษา (nginx)</td></tr>
<tr><td>{c("www.id-231.com/research")}</td><td>app-research</td><td>แสดงสรุปงานวิจัย</td></tr>
<tr><td>{c("www.id-231.com/api/<text>")}</td><td>app-api</td><td>แสดงข้อความตัวใหญ่กลางจอ</td></tr>
<tr><td>{c("admin.id-231.com")}</td><td>app-research</td><td>Ingress เปลี่ยน path เป็น {c("/edit")} เปิดหน้าแก้ไขและบันทึกสรุปงานวิจัย</td></tr>
</tbody></table>

<h2>2. ไฟล์ทั้งหมดของงาน</h2>
<p>ไฟล์ทั้งหมดอยู่ในโฟลเดอร์ <code>~/id-231</code> บนเครื่อง k8s-control โครงสร้างเดียวกับใน GitHub</p>
{shot("c02", "ไฟล์ในโฟลเดอร์งาน")}
<p>แอป <code>app-research</code> และ <code>app-api</code> เขียนด้วย Python (ใช้ http.server ที่มีมากับ Python) ส่วน <code>app-about</code> เป็นหน้า HTML
โค้ดและหน้าเว็บใส่เข้า Pod ผ่าน ConfigMap จึงใช้ image สำเร็จรูป <code>python:3.12-alpine</code> และ <code>nginx:1.25</code> ได้เลย ไม่ต้อง build image เอง</p>

<h2>3. K8s Manifest</h2>
<h3>3.1 Namespace</h3>
{shot("c03", "k8s/00-namespace.yaml")}
<h3>3.2 app-about</h3>
{shot("c04", "k8s/10-app-about.yaml", 200)}
<p>mount ConfigMap <code>app-about-web</code> (index.html กับ photo.jpg) ไว้ที่โฟลเดอร์เว็บของ nginx และ mount <code>app-about-conf</code> เป็น config ของ nginx ให้ตอบที่ path <code>/about</code></p>
{shot("c05", "apps/app-about/default.conf")}
<h3>3.3 app-research</h3>
{shot("c06", "k8s/20-app-research.yaml (PV, PVC, Deployment, Service)")}
<p>ข้อความสรุปงานวิจัยเก็บเป็นไฟล์ <code>/data/research.txt</code> บน PersistentVolume เพื่อให้ข้อมูลที่แก้ไขแล้วไม่หายเมื่อ Pod ถูกสร้างใหม่
PV เป็นแบบ hostPath อยู่บน k8s-worker1 จึงใช้ 1 replica และ strategy แบบ Recreate</p>
<h3>3.4 app-api</h3>
{shot("c07", "k8s/30-app-api.yaml", 200)}
<h3>3.5 Ingress</h3>
{shot("c08", "k8s/40-ingress.yaml", 215)}
<ul>
<li>Ingress <code>www-id-231</code> ใช้ host <code>www.id-231.com</code> แยก 3 path ไปที่ Service ของแต่ละแอป</li>
<li>Ingress <code>admin-id-231</code> ใช้ host <code>admin.id-231.com</code> และใส่ annotation <code>rewrite-target: /edit</code> ทุก request จึงถูกส่งไปที่ <code>/edit</code> ของ app-research</li>
</ul>
<h3>3.6 Ingress Controller</h3>
<p>ใช้ manifest ของ ingress-nginx v1.12.1 แบบ baremetal แก้อย่างเดียวคือกำหนด NodePort ให้คงที่เป็น 30081 (http) และ 30443 (https) เพื่อให้ LB ชี้มาได้</p>
{shot("c09", "NodePort ที่กำหนดใน ingress-controller/deploy.yaml")}

<h2>4. ขั้นตอนการสั่ง kubectl</h2>
<h3>4.1 ติดตั้ง Ingress Controller</h3>
{shot("c10", "apply ingress-nginx แล้วรอจน controller พร้อม")}
{shot("c11", "Pod, Service และ IngressClass ของ ingress-nginx")}
<h3>4.2 สร้าง Namespace และ ConfigMap</h3>
{shot("c12", "สร้าง namespace id-231 และ ConfigMap จากไฟล์ในโฟลเดอร์ apps")}
<h3>4.3 สร้าง Deployment และ Service</h3>
{shot("c13", "apply แอปทั้ง 3 ตัว แล้วรอ rollout")}
<h3>4.4 สร้าง Ingress</h3>
{shot("c14", "apply Ingress ทั้ง 2 ตัว")}
<p>ขั้นตอนทั้งหมดนี้รวมไว้ในไฟล์ <code>deploy.sh</code> สั่งครั้งเดียวได้</p>

<h2>5. External LB และ /etc/hosts</h2>
<p>บนเครื่อง <code>k8s-lb</code> เพิ่มไฟล์ <code>/etc/nginx/conf.d/www-id-231.conf</code> รับ request ของ 2 ชื่อนี้แล้วส่งต่อไปที่ NodePort 30081 ของทุก node
โดยส่ง header <code>Host</code> เดิมต่อไปด้วย เพราะ Ingress ใช้ชื่อ host ในการเลือกเส้นทาง</p>
{shot("l01", "config ของ LB สำหรับ id-231")}
{shot("l02", "ตรวจ config แล้ว reload NginX")}
<p>ชื่อ <code>id-231.com</code> ไม่ได้จดทะเบียนใน DNS จริง จึงเพิ่ม 2 บรรทัดใน <code>/etc/hosts</code> ของเครื่อง Linux ที่ใช้ทดสอบ ให้ชื่อทั้งสองชี้ไปที่ IP ของ LB ({c(LB_IP)})</p>
{shot("l03", "/etc/hosts ของเครื่อง Linux")}

<h2>6. การตรวจสอบการทำงาน</h2>
{shot("c01", "node ของ cluster")}
{shot("c15", "Deployment, ReplicaSet และ Pod ใน namespace id-231")}
{shot("c16", "Service, Endpoints, PV และ PVC")}
{shot("c19", "describe Service ทั้ง 3 ตัว")}
{shot("c17", "describe Ingress www-id-231")}
{shot("c18", "describe Ingress admin-id-231")}
<p>ใน describe เห็นว่าแต่ละ path ชี้ไปที่ Service และ Pod IP ถูกตัว และ Ingress ของ admin มี annotation rewrite-target เป็น /edit</p>
{shot("c20", "describe Deployment app-research")}

<h2>7. ทดสอบการเข้าใช้งาน</h2>
<p>ทดสอบจากเครื่อง Linux ที่ตั้ง /etc/hosts ไว้ เรียกด้วยชื่อ host ตรง ๆ ได้ 200 ทุกบริการ (ภาพหน้าจอของเว็บทุกหน้าอยู่ในไฟล์ผลการทดสอบ)</p>
{shot("l04", "ทดสอบ /about")}
{shot("l05", "ทดสอบ /research")}
{shot("l06", "ทดสอบ /api/&lt;ข้อความ&gt;")}
{shot("l07", "ทดสอบ admin.id-231.com")}
<p><code>www.id-231.com/edit</code> ได้ 404 เพราะหน้าแก้ไขเปิดให้เข้าทาง admin.id-231.com อย่างเดียว</p>
{shot("l08", "แก้ไขสรุปงานวิจัยผ่าน admin.id-231.com แล้วเปิด /research ดู")}
{shot("c21", "ลบ Pod ของ app-research แล้วดูไฟล์ข้อมูลใน Pod ใหม่")}
<p>หลังลบ Pod แล้ว Pod ตัวใหม่ยังอ่านข้อมูลที่แก้ไว้ได้ เพราะไฟล์อยู่บน PersistentVolume</p>
{shot("m01", "ทดสอบจากเครื่อง MacBook")}
<p>เครื่อง MacBook ไม่ได้แก้ /etc/hosts จึงใช้ <code>curl --resolve</code> ให้ชื่อชี้ไปที่ LB แทน ผลที่ได้เหมือนกัน และ header <code>Server</code> เป็นของ NginX บนเครื่อง LB</p>
{shot("l10", "access log ของ LB")}
{shot("c22", "log ของ Ingress Controller นับตาม path และ Service ปลายทาง")}
<p>ใน log ของ Ingress Controller เห็นว่า /about ไป app-about, /research ไป app-research, /api ไป app-api และ request ของ admin (path /) ไปที่ app-research</p>

<h2>8. สรุป</h2>
<ul>
<li>เข้าใช้บริการได้ครบ 4 รายการตามโจทย์ ด้วยชื่อ www.id-231.com และ admin.id-231.com</li>
<li>Ingress เป็นตัวแยกเส้นทางตาม host และ path ไปที่ Service แบบ ClusterIP ของแต่ละแอป ไม่ต้องเปิด NodePort แยกทีละแอป</li>
<li>admin.id-231.com ใช้ app-research ตัวเดียวกับ /research แต่ถูก rewrite ไปที่ /edit และข้อมูลที่บันทึกเก็บบน PersistentVolume</li>
</ul>
</body></html>"""
(HERE / "report.html").write_text(REPORT)
N_REPORT = FIG[0]

FIG[0] = 0
TEST = f"""<!doctype html><html lang="th"><head><meta charset="utf-8"><title>CT655 id-231 test</title><style>{CSS}</style></head><body>
{WHO}
<h2>ผลการทดสอบการทำงานของ service ทุกตัว</h2>
<p>เปิดด้วย Chrome บนเครื่อง MacBook โดยให้ชื่อ www.id-231.com และ admin.id-231.com ชี้ไปที่ External LB ({c(LB_IP)})</p>
<h3>1. www.id-231.com/about (app-about)</h3>
{web("w1-about", "หน้า about แสดงรูป ชื่อ และรหัสนักศึกษา")}
{shot("l04", "เรียก /about ด้วย curl จากเครื่อง Linux")}
<h3>2. www.id-231.com/research (app-research)</h3>
{web("w2-research", "หน้าสรุปงานวิจัย")}
{shot("l05", "เรียก /research ด้วย curl")}
<h3>3. www.id-231.com/api/&lt;ข้อความ&gt; (app-api)</h3>
{web("w3-api", "ข้อความ Hello K8s ตัวใหญ่กลางจอ", 130)}
{web("w4-api-id", "เปลี่ยนข้อความใน URL หน้าเว็บก็เปลี่ยนตาม", 130)}
{shot("l06", "เรียก /api ด้วย curl คำตอบสลับกันมาจาก Pod 2 ตัว")}
<h3>4. admin.id-231.com (app-research /edit)</h3>
{web("w5-admin", "หน้าแก้ไขสรุปงานวิจัย", 140)}
{shot("l07", "เรียก admin.id-231.com ด้วย curl")}
<h3>5. แก้ไขแล้วบันทึกกลับ</h3>
{shot("l08", "ส่งข้อมูลที่แก้ไข (POST) ผ่าน admin.id-231.com")}
{web("w6-admin-after", "หน้าแก้ไขหลังบันทึก ชื่อเรื่องเปลี่ยนแล้ว", 140)}
{web("w7-research-after", "หน้า /research แสดงชื่อเรื่องที่แก้ไข", 140)}
{shot("c21", "ลบ Pod ของ app-research")}
{shot("l09", "หลัง Pod ถูกสร้างใหม่ ข้อมูลที่แก้ไขยังอยู่")}
<h3>6. Service ใน cluster</h3>
{shot("c16", "Service, Endpoints, PV และ PVC")}
{shot("c22", "log ของ Ingress Controller แสดง Service ปลายทางของแต่ละ path")}
</body></html>"""
(HERE / "test.html").write_text(TEST)


def chrome(*a):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", *a], capture_output=True, check=True, timeout=180)


chrome("--force-device-scale-factor=2", f"--window-size={W},{H}", f"--screenshot={HERE / 'diagram.png'}",
       "--virtual-time-budget=3000", (HERE / "diagram.html").as_uri())
for n in ("report", "test"):
    chrome("--no-pdf-header-footer", f"--print-to-pdf={HERE / (n + '.pdf')}", "--virtual-time-budget=8000", (HERE / (n + ".html")).as_uri())
print("done", N_REPORT, "+", FIG[0], "figures")
