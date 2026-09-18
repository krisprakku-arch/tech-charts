"""BBL-style technical chart cards: candle chart (left) + info panel (right). Test first."""
import pandas as pd, json, sys, textwrap, os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle
import matplotlib.gridspec as gs

OUT = Path(os.environ.get("TECH_DATA_DIR", "/tmp/tech_analysis"))
OUT.mkdir(parents=True, exist_ok=True)
TH = FontProperties(family="Sarabun")
THB = FontProperties(family="Sarabun", weight="bold")
UP, DN = "#26a69a", "#ef5350"

def rsi_sig(r):
    if r <= 35: return "Buy"
    if r >= 65: return "Sell"
    return "Neutral"

def narrative(name, trend, r, sr, e50, e200, cur):
    t1 = {"UPTREND": f"{name} ยังอยู่ในแนวโน้มขาขึ้น", "DOWNTREND": f"{name} อยู่ในแนวโน้มขาลง"}.get(
        trend.split()[0], f"{name} แกว่งตัวในกรอบออกข้าง")
    pos = "ยืนเหนือ" if cur > e50 else "หลุดต่ำกว่า"
    t2 = f"ล่าสุด{pos}เส้น EMA50 ที่ {e50:,.2f}"
    t3 = {"Buy": f"RSI {r:.1f} เข้าโซนซื้อ มีลุ้นรีบาวด์", "Sell": f"RSI {r:.1f} เข้าโซนขาย ระวังพักฐาน",
          "Neutral": f"RSI {r:.1f} อยู่โซนกลาง"}[rsi_sig(r)]
    t4 = f"กรอบสำคัญ ต้าน {sr['R1']:,.2f}/{sr['R2']:,.2f} รับ {sr['S1']:,.2f}/{sr['S2']:,.2f}"
    return f"{t1} {t2} {t3} {t4}"

def card(key, title, df, trend, reason, r, sr):
    df = df.iloc[-250:].copy()
    sig = rsi_sig(r)
    cur = float(df["Close"].iloc[-1])
    e50, e200 = float(df["EMA50"].iloc[-1]), float(df["EMA200"].iloc[-1])
    fig = plt.figure(figsize=(12, 7))
    fig.patch.set_facecolor("#f4f4f4")
    fig.text(0.03, 0.94, f"Technical Chart: {title}", fontproperties=THB, fontsize=16)
    fig.text(0.97, 0.94, "Bangkok Bank CIO", fontproperties=TH, fontsize=10, ha="right", color="#8a7a3a")
    g = gs.GridSpec(2, 2, width_ratios=[3.1, 1], height_ratios=[3, 1],
                    left=0.065, right=0.97, top=0.89, bottom=0.08, wspace=0.06, hspace=0.25)
    ax = fig.add_subplot(g[0, 0]); ax.set_facecolor("white")
    axr = fig.add_subplot(g[1, 0], sharex=ax); axr.set_facecolor("white")
    info = fig.add_subplot(g[:, 1]); info.axis("off")
    # candles
    w = 0.7
    for i, (_, row) in enumerate(df.iterrows()):
        o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
        col = UP if c >= o else DN
        ax.plot([i, i], [l, h], color=col, lw=0.8)
        ax.add_patch(Rectangle((i - w/2, min(o, c)), w, max(abs(c - o), 1e-9), facecolor=col, edgecolor=col))
    ax.plot(range(len(df)), df["EMA50"], color="#2962FF", lw=1.1, label="EMA50")
    ax.plot(range(len(df)), df["EMA200"], color="#E91E63", lw=1.1, label="EMA200")
    xr = 1
    for lvl, col, ls, lbl in [(sr["R2"], "#c0392b", "--", "R2"), (sr["R1"], "#e67e22", "--", "R1"),
                              (sr["S1"], "#0a7a42", "--", "S1"), (sr["S2"], "#0a7a42", ":", "S2")]:
        ax.axhline(lvl, color=col, ls=ls, lw=1.0)
        ax.text(xr, lvl, f" {lbl} {lvl:,.2f} ", color="white", fontsize=8, fontweight="bold",
                va="center", ha="left", alpha=0.92,
                bbox=dict(facecolor=col, edgecolor="none", boxstyle="round,pad=0.3"))
    ax.set_xlim(-0.8, len(df) + 1)
    ax.legend(fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=True); ax.grid(alpha=0.2)
    ax.set_xticklabels([])
    # RSI
    axr.plot(range(len(df)), df["RSI14"], color="#2962FF", lw=1.1)
    axr.axhline(70, color="red", ls="--", lw=0.8); axr.axhline(30, color="green", ls="--", lw=0.8)
    axr.set_ylim(0, 100); axr.grid(alpha=0.2)
    months = [i for i in range(len(df)) if df.index[i].day <= 7 and (i == 0 or df.index[i].month != df.index[i-1].month)]
    axr.set_xticks(months)
    axr.set_xticklabels([df.index[i].strftime("%b") for i in months], fontsize=8)
    # info panel
    rows = [["แนวโน้มหลัก", trend], ["ราคาล่าสุด", f"{cur:,.2f}"],
            ["แนวรับ", f"{sr['S1']:,.2f}, {sr['S2']:,.2f}"],
            ["แนวต้าน", f"{sr['R1']:,.2f}, {sr['R2']:,.2f}"], ["RSI (Signal)", sig]]
    tab = info.table(cellText=rows, colWidths=[0.38, 0.62], loc="upper center",
                     bbox=[0, 0.58, 1, 0.40])
    tab.auto_set_font_size(False); tab.set_fontsize(10)
    for (ri, ci), cell in tab.get_celld().items():
        cell.set_text_props(fontproperties=THB if ci == 0 else TH)
        if ri == 0:
            cell.set_facecolor("#1e5bb0"); cell.set_text_props(color="white", fontproperties=THB)
        elif ri in (1, 3):
            cell.set_facecolor("#ececec")
        else:
            cell.set_facecolor("white")
    info.text(0, 0.56, "แนวโน้ม:", fontproperties=THB, fontsize=11, va="top", ha="left")
    info.text(0, 0.50, "\n".join(textwrap.wrap(
        narrative(title, trend, r, sr, e50, e200, cur), width=32)),
        fontproperties=TH, fontsize=10, va="top", ha="left", linespacing=1.6)
    fig.text(0.03, 0.02, "© Bangkok Bank", fontproperties=TH, fontsize=8)
    fig.text(0.5, 0.02, "Internal Use Only", fontsize=8, color="red", ha="center", weight="bold")
    fig.text(0.97, 0.02, f"ที่มา: Yahoo Finance ณ วันที่ {df.index[-1].date()}",
             fontproperties=TH, fontsize=8, ha="right")
    fig.savefig(OUT / f"{key}_card.png", dpi=150)
    plt.close(fig)
    print("CARD_OK", key, sig)

if __name__ == "__main__":
    summ = json.loads((OUT / "sr_summary_v2.json").read_text(encoding="utf-8"))
    only = sys.argv[1:] or list(summ.keys())
    names = {"SP500": "S&P 500", "BRENT": "Brent", "XAU": "ทองคำ", "NASDAQ": "Nasdaq",
             "US10Y": "US 10Y", "STOXX600": "STOXX 600", "SET": "SET Index",
             "SSE": "SSE Composite", "HSI": "HSI",
             "HSCEI": "HSCEI", "NIKKEI225": "Nikkei 225", "SENSEX": "Sensex", "USDTHB": "USD/THB"}
    done = 0
    for key in only:
        csv = OUT / f"{key}_daily.csv"
        if key not in summ or not csv.exists():
            print(f"SKIP {key}: ไม่มีข้อมูล (ถูกข้ามจากขั้นดึงข้อมูล)")
            continue
        df = pd.read_csv(csv, parse_dates=["Date"], index_col="Date")
        s = summ[key]
        card(key, names.get(key, key), df, s["trend"], s["reason"], s["rsi"], s["sr"])
        done += 1
    print("DONE_CARDS", done)
