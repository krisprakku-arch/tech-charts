"""Send technical charts via SMTP with Thai SR summary report in body."""
import os, sys, smtplib, json
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.header import Header

ROOT = Path(__file__).resolve().parent  # .../Tech_Charts
BASE = Path(os.environ.get("TECH_ENV_DIR", str(ROOT.parent)))  # โฟลเดอร์ที่มี .env (default: โฟลเดอร์แม่)
OUT = Path(os.environ.get("TECH_DATA_DIR", "/tmp/tech_analysis"))
OUT.mkdir(parents=True, exist_ok=True)
env = {}
for line in (BASE/".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k,v = line.split("=",1)
        env[k.strip()] = v.strip()

SMTP_SERVER = env.get("SMTP_SERVER","smtp.gmail.com")
SMTP_PORT = int(env.get("SMTP_PORT","587"))
SMTP_USER = env.get("SMTP_USERNAME","")
SMTP_PASS = env.get("SMTP_PASSWORD","")
SMTP_FROM = env.get("SMTP_FROM", SMTP_USER)
TO_LIST = [a.strip() for a in env.get("TECH_CHART_TO", env.get("SMTP_TO",SMTP_USER)).split(",") if a.strip()]

FILES = ["SP500","NASDAQ","US10Y","STOXX600","SET","SSE","HSCEI","NIKKEI225","SENSEX","XAU","USDTHB","BRENT"]
TNAMES = {"SP500":"S&P 500 (สหรัฐ)","NASDAQ":"Nasdaq (สหรัฐ)","US10Y":"US 10Y Yield (สหรัฐ)","STOXX600":"STOXX 600 (ยุโรป)","SET":"SET Index (ไทย)",
          "SSE":"SSE Composite (เซี่ยงไฮ้)",
          "HSCEI":"HSCEI (ฮ่องกง-จีน)","NIKKEI225":"Nikkei 225 (ญี่ปุ่น)","SENSEX":"Sensex (อินเดีย)",
          "XAU":"ทองคำ","USDTHB":"USD/THB","BRENT":"น้ำมัน Brent"}
summ = json.loads((OUT/"sr_summary_v2.json").read_text(encoding="utf-8"))
status = json.loads((OUT/"run_status.json").read_text(encoding="utf-8")) if (OUT/"run_status.json").exists() else {"ok":list(summ.keys()),"skipped":{}}
skipped = status.get("skipped", {})
# เอาเฉพาะตลาดที่มีข้อมูล + การ์ดจริง
FILES = [k for k in FILES if k in summ and (OUT/f"{k}_card.png").exists()]

def trend_tag(trend):
    t = trend.upper()
    if "UPTREND" in t: return "🟢"
    if "DOWNTREND" in t: return "🔴"
    return "🟡"

def reading(key, s, sr, cur):
    notes = []
    rsi = s.get("rsi", 50)
    weak = rsi < 50 or "DOWN" in s.get("trend","").upper()
    if rsi >= 70: notes.append("RSI เข้าเขตซื้อมาก ระวังพักฐาน")
    elif rsi <= 30: notes.append("RSI เข้าขายมาก ลุ้นรีบาวด์")
    elif rsi <= 35: notes.append("RSI ใกล้ขายมาก โมเมนตัมอ่อน ระวังลงต่อ")
    r1, s1 = sr.get("R1",cur), sr.get("S1",cur)
    if abs(cur-r1)/r1 < 0.01:
        notes.append(f"ติดต้าน R1 {r1:,.2f} ระวังย่อ" if weak else f"จ่อทดสอบต้าน R1 {r1:,.2f}")
    elif abs(cur-s1)/s1 < 0.01:
        notes.append(f"ยั้งเหนือรับ S1 {s1:,.2f} เปราะบาง หลุดเจอ S2" if weak else f"ยั้งเหนือรับ S1 {s1:,.2f}")
    elif cur > r1: notes.append("ทะลุต้าน R1 ขึ้นมา ลุ้นไป R2")
    elif cur < s1: notes.append("หลุดรับ S1 ระวังลงหา S2")
    return " / ".join(notes) if notes else "เคลื่อนในกรอบ รอเบรก R1/S1"

L = []
L.append("เรียน CIO Team,")
L.append("")
L.append(f"รายงานเทคนิคย่อรายวัน — กราฟแท่งเทียน + EMA50/200 + RSI + แนวรับ/แนวต้าน ({len(FILES)} ตลาด, รายละเอียดในไฟล์แนบ PNG)")
if skipped:
    L.append("⚠️ ไม่มีข้อมูลในฉบับนี้: " + " | ".join(f"{k} — {v}" for k, v in sorted(skipped.items())))
    L.append("   (ดึงข้อมูลจากแหล่งข้อมูลไม่ครบ ระบบข้ามเพื่อกันกราฟผิดพลาด จะกลับมาเองเมื่อแหล่งข้อมูลปกติ)")
L.append("="*60)
up = sum(1 for k in FILES if "UPTREND" in summ.get(k,{}).get("trend",""))
down = sum(1 for k in FILES if "DOWN" in summ.get(k,{}).get("trend","").upper())
L.append(f"ภาพรวม: 🟢ขาขึ้น {up} ตลาด / 🔴ขาลง-พักลง {down} ตลาด / 🟡ออกข้าง {len(FILES)-up-down} ตลาด")
L.append("="*60)
for k in FILES:
    s = summ.get(k,{}); sr = s.get("sr",{}); cur = s.get("close",0)
    tag = trend_tag(s.get("trend",""))
    L.append(f"{tag} [{k} | {TNAMES[k]}]")
    L.append(f"  ปิด {cur:,.2f} ({s.get('chg_pct',0):+.2f}%) วันที่ {s.get('date','')} | แนวโน้ม: {tag} {s.get('trend','')} | RSI {s.get('rsi',0):.1f}")
    L.append(f"  ต้าน R2 {sr.get('R2',0):,.2f} / R1 {sr.get('R1',0):,.2f} | รับ S1 {sr.get('S1',0):,.2f} / S2 {sr.get('S2',0):,.2f}")
    L.append(f"  อ่าน: {reading(k,s,sr,cur)}")
    L.append("")
L.append("หมายเหตุ: แนวรับ/ต้านจาก High/Low 20-60 วัน + EMA + Bollinger + เลขจิตวิทยา เพื่อประกอบการตัดสินใจ ไม่ใช่คำแนะนำซื้อขาย")
L.append("ที่มา: Yahoo Finance | จัดทำโดย Hermes Agent (cron ทุกเสาร์ 08:00)")
body = "\n".join(L)

if "--preview" in sys.argv:
    print(body)
    raise SystemExit(0)

if "--to" in sys.argv:
    TO_LIST = [sys.argv[sys.argv.index("--to")+1].strip()]

msg = MIMEMultipart()
msg["From"] = SMTP_FROM
msg["To"] = ", ".join(TO_LIST)
msg["Subject"] = Header(f"📈 Technical Daily (Candle+RSI+SR): สรุปแนวรับ-แนวต้าน {len(FILES)} ตลาด — ฉบับย่อในเมล์ + กราฟแนบ", "utf-8")
msg.attach(MIMEText(body, "plain", "utf-8"))
for k in FILES:
    p = OUT/f"{k}_card.png"
    if p.exists():
        with open(p,"rb") as f:
            img = MIMEImage(f.read(), _subtype="png")
            img.add_header("Content-Disposition","attachment",filename=p.name)
            msg.attach(img)
    else:
        print(f"missing {p}")
pdf = OUT/"Technical_Charts_Weekly.pdf"
if pdf.exists():
    with open(pdf,"rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header("Content-Disposition","attachment",filename=pdf.name)
        msg.attach(part)
else:
    print("missing Technical_Charts_Weekly.pdf")

try:
    sv = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
    sv.starttls(); sv.login(SMTP_USER, SMTP_PASS)
    sv.sendmail(SMTP_FROM, TO_LIST, msg.as_string()); sv.quit()
    print(f"SENT_OK to {len(TO_LIST)} recipients, {len(FILES)} cards + PDF")
except Exception as e:
    print(f"SEND_FAIL: {type(e).__name__}: {e}")
