"""V2: Price + RSI only + SR, 8 symbols."""
import yfinance as yf, pandas as pd, json, math, os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

OUT = Path(os.environ.get("TECH_DATA_DIR", "/tmp/tech_analysis"))
OUT.mkdir(parents=True, exist_ok=True)
SYMBOLS = {
    "SP500": "^GSPC",
    "US10Y": "^TNX",
    "NASDAQ": "^IXIC",
    "STOXX600": "^STOXX",
    "SET": "^SET.BK",
    "SSE": "000001.SS",
    "HSCEI": "^HSCE",
    "NIKKEI225": "^N225",
    "SENSEX": "^BSESN",
    "XAU": "GC=F",
    "USDTHB": "THB=X",
    "BRENT": "BZ=F",
}
NAMES = {
    "SP500":"S&P 500 (US)", "NASDAQ":"Nasdaq Composite (US)", "US10Y":"US 10Y Treasury Yield",
    "STOXX600":"STOXX 600 (Europe)",
    "SET":"SET Index (Thailand)", "SSE":"SSE Composite (China)", "HSCEI":"HSCEI (HK China)",
    "NIKKEI225":"Nikkei 225 (Japan)", "SENSEX":"Sensex 30 (India)",
    "XAU":"Gold Futures (GC=F)",
    "USDTHB":"USD/THB", "BRENT":"Brent Oil Futures",
}
UNITS = {"SP500":"pts","NASDAQ":"pts","STOXX600":"pts","SET":"pts","SSE":"pts","HSCEI":"pts","NIKKEI225":"pts","SENSEX":"pts","XAU":"$/oz","USDTHB":"THB","BRENT":"$/bbl","US10Y":"%"}

def rsi(close, n=14):
    d = close.diff()
    ag = d.where(d>0,0.0).ewm(alpha=1/n,min_periods=n,adjust=False).mean()
    al = (-d.where(d<0,0.0)).ewm(alpha=1/n,min_periods=n,adjust=False).mean()
    return 100-(100/(1+ag/al.replace(0,1e-9)))

def atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return float(tr.ewm(alpha=1/n, min_periods=n, adjust=False).mean().iloc[-1])

def calc_sr(df):
    recent = df.iloc[-60:]; cur=float(df["Close"].iloc[-1])
    hi_s=float(recent["High"].iloc[-20:].max()); lo_s=float(recent["Low"].iloc[-20:].min())
    hi_l=float(recent["High"].max()); lo_l=float(recent["Low"].min())
    e50=float(df["EMA50"].iloc[-1]); e200=float(df["EMA200"].iloc[-1])
    bb_up=float(df["BB_UP"].iloc[-1]); bb_lo=float(df["BB_LO"].iloc[-1])
    step = 500 if cur>=10000 else 100 if cur>=1000 else 10 if cur>=100 else 1
    psy_up=math.ceil(cur/step)*step; psy_lo=math.floor(cur/step)*step
    a = atr(df)
    min_gap = max(a*1.0, cur*0.01)  # แนวที่ 2 ต้องห่างจากแนวที่ 1 อย่างน้อย ~1.0 ATR หรือ 1.0%
    win = min_gap*2  # แต่ไม่ไกลเกิน 2 เท่าของ min_gap ไม่งั้น fallback (ใช้ไม่ได้จริง)
    cR=sorted(set(x for x in [hi_s,hi_l,bb_up,psy_up,e50,e200] if x>cur*1.001))
    cS=sorted(set(x for x in [lo_s,lo_l,bb_lo,psy_lo,e50,e200] if x<cur*0.999),reverse=True)
    r1 = cR[0] if cR else cur*1.03
    r2c = [x for x in cR if r1+min_gap <= x <= r1+win]
    r2 = r2c[0] if r2c else r1+min_gap
    s1 = cS[0] if cS else cur*0.97
    s2c = [x for x in cS if s1-win <= x <= s1-min_gap]
    s2 = s2c[0] if s2c else s1-min_gap
    # S1/R1 ใช้แนวใกล้สุดเหมือนเดิม ส่วน S2/R2 ใช้แนวชั้นลึก (ห่าง มีนัยสำคัญ)
    r0, s0 = r1, s1
    r3c = [x for x in cR if r2+min_gap <= x <= r2+win]
    r1, r2 = r0, (r3c[0] if r3c else r2+min_gap)
    s3c = [x for x in cS if s2-win <= x <= s2-min_gap]
    s1, s2 = s0, (s3c[0] if s3c else s2-min_gap)
    # ปัดเศษตามขนาดราคา + บังคับให้ R2>R1>Close>S1>S2 หลังปัด (กันป้ายซ้ำจาก rounding)
    dg = 0 if cur >= 1000 else (1 if cur >= 100 else 2)
    cr = round(cur, dg)
    r1 = round(r1, dg); r2 = round(r2, dg); s1 = round(s1, dg); s2 = round(s2, dg)
    mg = round(min_gap, dg) or 10**-dg
    if r1 <= cr: r1 = round(cr + mg, dg)
    if r2 - r1 < mg: r2 = round(r1 + mg, dg)
    if s1 >= cr: s1 = round(cr - mg, dg)
    if s1 - s2 < mg: s2 = round(s1 - mg, dg)
    return {"R2":r2,"R1":r1,"S1":s1,"S2":s2,"EMA50":e50,"EMA200":e200,"ATR":a}

def trend(df):
    last=df.iloc[-1]; c=float(last["Close"]); e50=float(last["EMA50"]); e200=float(last["EMA200"]); r=float(last["RSI14"])
    slope=(e50-float(df["EMA50"].iloc[-11]))/float(df["EMA50"].iloc[-11])*100
    if c>e50>e200 and slope>0: return ("UPTREND" if r<70 else "UPTREND (hot)", f"Above EMA50/200, EMA50 slope {slope:+.2f}%/10d, RSI {r:.1f}")
    if c<e50<e200 and slope<0: return ("DOWNTREND" if r>30 else "DOWNTREND (washed)", f"Below EMA50/200, EMA50 slope {slope:+.2f}%/10d, RSI {r:.1f}")
    if c>e50 and c>e200: return ("Sideways-up", f"Holding above averages, RSI {r:.1f} — watching R1")
    if c<e50 and c<e200: return ("Sideways-down", f"Below averages, RSI {r:.1f} — watching S1 for bounce")
    return ("SIDEWAYS", f"Wrapping EMA50, RSI {r:.1f} — wait for R1/S1 break")

full={}
skipped={}
MIN_ROWS = 200  # ต้องมีอย่างน้อยพอคำนวณ EMA200 + ATR14 ไม่งั้นการ์ดจะได้ nan
for key,ticker in SYMBOLS.items():
    print(f"Fetching {key} {ticker}...")
    df=yf.download(ticker,period="2y",interval="1d",auto_adjust=True,progress=False)
    if df is None or df.empty: print(f" FAIL {key}"); skipped[key]="ไม่มีข้อมูลจาก Yahoo"; continue
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    df=df.dropna()
    if len(df) < MIN_ROWS:
        skipped[key]=f"ข้อมูลย้อนหลังไม่พอ ({len(df)} แท่ง < {MIN_ROWS}) — ฟีดขาด คำนวณ EMA200/ATR ไม่ได้"
        print(f" SKIP {key}: {skipped[key]}")
        continue
    df["EMA50"]=df["Close"].ewm(span=50,adjust=False).mean()
    df["EMA200"]=df["Close"].ewm(span=200,adjust=False).mean()
    df["RSI14"]=rsi(df["Close"])
    ma20=df["Close"].rolling(20).mean(); sd=df["Close"].rolling(20).std()
    df["BB_UP"]=ma20+2*sd; df["BB_LO"]=ma20-2*sd
    df.to_csv(OUT/f"{key}_daily.csv")
    sr=calc_sr(df); t,reason=trend(df); cur=float(df["Close"].iloc[-1]); prev=float(df["Close"].iloc[-2])
    chg=(cur-prev)/prev*100
    full[key]={"close":cur,"chg_pct":chg,"date":str(df.index[-1].date()),"trend":t,"reason":reason,"rsi":float(df["RSI14"].iloc[-1]),"sr":sr,"unit":UNITS[key]}
    import mplfinance as mpf
    title=f"{NAMES[key]} Daily Candle — {t} | Close {cur:,.2f} ({chg:+.2f}%) {df.index[-1].date()}"
    ap=[mpf.make_addplot(df["EMA50"],color="#1e5bb0",width=1.0),
        mpf.make_addplot(df["EMA200"],color="#b89300",width=1.0),
        mpf.make_addplot(df["RSI14"],panel=1,color="#6a3fb5",width=1.1,ylim=(0,100))]
    hl=dict(hlines=[sr["R2"],sr["R1"],sr["S1"],sr["S2"]],
            colors=["#c0392b","#e67e22","#0a7a42","#0a7a42"],
            linestyle=["--","--","--",":"],linewidths=[1.0,1.0,1.0,1.0])
    fig,axes=mpf.plot(df[["Open","High","Low","Close"]],type="candle",style="yahoo",
        addplot=ap,hlines=hl,panel_ratios=(3,1),figsize=(10,6.8),
        title=title,ylabel="Price",ylabel_lower="RSI14",returnfig=True)
    ax=axes[0]
    xleft=ax.get_xlim()[0]+2
    lvls=[(sr["R2"],"#c0392b","R2"),(sr["R1"],"#e67e22","R1"),(sr["S1"],"#0a7a42","S1"),(sr["S2"],"#0a7a42","S2")]
    placed=[]
    for i,(lvl,col,lbl) in enumerate(lvls):
        va="center"; xoff=0
        for (plvl,pxoff) in placed:
            if abs(lvl-plvl)/max(abs(lvl),1e-9)<0.012:
                va="bottom" if lvl>=plvl else "top"; xoff=pxoff+28
        placed.append((lvl,xoff))
        ax.text(xleft+xoff,lvl,f" {lbl} {lvl:,.2f} ",color="white",fontsize=7.5,fontweight="bold",va=va,ha="left",bbox=dict(facecolor=col,edgecolor="none",boxstyle="round,pad=0.3"))
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0],[0],color="#1e5bb0",lw=1.5),Line2D([0],[0],color="#b89300",lw=1.5)],labels=["EMA50","EMA200"],fontsize=8,loc="best")
    rax=axes[2] if len(axes)>2 else axes[1]
    rax.axhline(70,color="red",ls="--",lw=0.8); rax.axhline(30,color="green",ls="--",lw=0.8)
    fig.text(0.5,0.01,f"Trend: {t} — {reason}",ha="center",fontsize=8.5,style="italic",bbox=dict(facecolor="#f0f6ff",edgecolor="#c8dcff",boxstyle="round,pad=0.4"))
    fig.tight_layout(rect=[0,0.04,1,0.95]); fig.savefig(OUT/f"{key}_daily_v2.png",dpi=150); plt.close(fig)
    print(f" OK {key}: {t} {cur:,.2f} R1 {sr['R1']:,.2f} S1 {sr['S1']:,.2f}")
(OUT/"sr_summary_v2.json").write_text(json.dumps(full,ensure_ascii=False,indent=2),encoding="utf-8")
(OUT/"run_status.json").write_text(json.dumps({"ok":list(full.keys()),"skipped":skipped},ensure_ascii=False,indent=2),encoding="utf-8")
if skipped:
    print("SKIPPED_SYMBOLS:", ", ".join(f"{k} ({v})" for k,v in skipped.items()))
print("DONE_V2")
