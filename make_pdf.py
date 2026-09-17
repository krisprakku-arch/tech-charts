"""Build PDF: cover + 1 card per page."""
import json, os
from pathlib import Path
from datetime import date
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from PIL import Image

OUT = Path(os.environ.get("TECH_DATA_DIR", "/tmp/tech_analysis"))
OUT.mkdir(parents=True, exist_ok=True)
ORDER = ["SP500","NASDAQ","US10Y","STOXX600","SET","SSE","HSCEI","NIKKEI225","SENSEX","XAU","USDTHB","BRENT"]
TNAMES = {"SP500":"S&P 500 (สหรัฐ)","NASDAQ":"Nasdaq (สหรัฐ)","US10Y":"US 10Y Yield",
          "STOXX600":"STOXX 600 (ยุโรป)","SET":"SET Index (ไทย)",
          "SSE":"SSE Composite (จีน)",
          "HSCEI":"HSCEI (ฮ่องกง-จีน)","NIKKEI225":"Nikkei 225 (ญี่ปุ่น)",
          "SENSEX":"Sensex (อินเดีย)","XAU":"ทองคำ","USDTHB":"USD/THB","BRENT":"น้ำมัน Brent"}
TH = FontProperties(family="Sarabun"); THB = FontProperties(family="Sarabun", weight="bold")

summ = json.loads((OUT/"sr_summary_v2.json").read_text(encoding="utf-8"))
status = json.loads((OUT/"run_status.json").read_text(encoding="utf-8")) if (OUT/"run_status.json").exists() else {"ok":list(summ.keys()),"skipped":{}}
skipped = status.get("skipped", {})
today = date.today().strftime("%d %B %Y")
# เอาเฉพาะตลาดที่มีการ์ดจริง (กัน PDF พังเมื่อฟีดตัวใดตัวหนึ่งขาด)
cards = [k for k in ORDER if (OUT/f"{k}_card.png").exists()]
missing = [k for k in ORDER if k not in cards]
ORDER = cards

def tag(t):
    t = t.upper()
    if "UPTREND" in t: return "🟢"
    if "DOWNTREND" in t: return "🔴"
    return "🟡"

# cover
fig = plt.figure(figsize=(11.7, 8.3))
fig.patch.set_facecolor("#0a2240")
fig.text(0.5, 0.72, "Technical Charts", fontsize=44, color="white", ha="center", weight="bold")
fig.text(0.5, 0.62, "กราฟแท่งเทียน + EMA50/200 + RSI + แนวรับ-แนวต้าน", fontproperties=TH, fontsize=20, color="#ffd84d", ha="center")
fig.text(0.5, 0.50, f"{len(ORDER)} ตลาด  •  ข้อมูล ณ {today}", fontproperties=TH, fontsize=14, color="white", ha="center")
if skipped or missing:
    miss = sorted(set(list(skipped.keys()) + missing))
    fig.text(0.5, 0.40, "ไม่มีข้อมูลในฉบับนี้: " + ", ".join(miss), fontproperties=TH, fontsize=11, color="#ff9a9a", ha="center")
fig.text(0.5, 0.06, "Bangkok Bank CIO  •  Internal Use Only", fontproperties=TH, fontsize=10, color="#8a9cc0", ha="center")
fig.savefig(OUT/"_cover.png", dpi=150)
plt.close(fig)

imgs = [Image.open(OUT/"_cover.png").convert("RGB")]
for k in ORDER:
    imgs.append(Image.open(OUT/f"{k}_card.png").convert("RGB"))
pdf_path = OUT/"Technical_Charts_Weekly.pdf"
imgs[0].save(pdf_path, save_all=True, append_images=imgs[1:])
print("PDF_OK", pdf_path, f"{len(imgs)} pages, {pdf_path.stat().st_size/1024:.0f} KB")
