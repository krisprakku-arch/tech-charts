# Technical Charts — กราฟเทคนิครายสัปดาห์ (BBL CIO)

ดึงราคาจาก Yahoo Finance → คำนวณ EMA50/200 + RSI14 + แนวรับ/แนวต้าน (ATR-based)
→ วาดการ์ดกราฟ (candlestick + RSI) → รวม PDF → ส่งอีเมล สรุปภาษาไทย

ครอบคลุม 12 ตลาด: S&P500, Nasdaq, US10Y, STOXX600, SET, SSE Composite,
HSCEI, Nikkei225, Sensex, ทองคำล่วงหน้า (GC=F), USD/THB, Brent

## ติดตั้ง (ทำครั้งเดียว)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # แล้วกรอก Gmail + App Password + รายชื่อผู้รับ
```

> Gmail ต้องใช้ **App Password** (ไม่ใช่รหัสปกติ) — สร้างที่ Google Account → Security

ฟอนต์ไทย: สคริปต์ใช้ฟอนต์ `Sarabun` ถ้าเครื่องไม่มี ติดตั้งก่อน
(macOS: `brew install --cask font-sarabun` หรือโหลด TTF มาลง)

## วิธีรัน (ตามลำดับ)

```bash
source .venv/bin/activate
python fetch_weekly_tech.py            # 1. ดึงข้อมูล → CSV + sr_summary_v2.json ใน $TECH_DATA_DIR (default /tmp/tech_analysis)
python chart_cards.py SP500 NASDAQ US10Y STOXX600 SET SSE HSCEI NIKKEI225 SENSEX XAU USDTHB BRENT  # 2. วาดการ์ด
python make_pdf.py                     # 3. รวม PDF (ปก + ตลาดละ 1 หน้า)
python send_charts_mail.py --preview   # 4. ดูตัวอย่างเนื้อหาเมล์ก่อนส่ง
python send_charts_mail.py             # 5. ส่งจริงตาม TECH_CHART_TO
python send_charts_mail.py --to someone@gmail.com  # ส่งทดสอบคนเดียว
python add_recipient.py someone@gmail.com          # เพิ่มผู้รับเข้า .env
```

## ตัวแปรแวดล้อม (ไม่บังคับ)

| ตัวแปร | default | ใช้ทำอะไร |
|---|---|---|
| `TECH_DATA_DIR` | `/tmp/tech_analysis` | ที่เก็บ CSV/PNG/PDF/JSON ระหว่างรัน |
| `TECH_ENV_DIR` | โฟลเดอร์แม่ของสคริปต์ | ที่อยู่ของไฟล์ `.env` |
| `TECH_ENV_FILE` | `<TECH_ENV_DIR>/.env` | path ไฟล์ `.env` ตรงๆ (ใช้กับ add_recipient) |

## หมายเหตุ

- ทองคำใช้ฟีดฟิวเจอร์ส `GC=F` (Yahoo เลิกให้ฟีด XAU spot แล้ว)
- แนวรับ/ต้านจาก High/Low 20–60 วัน + EMA + Bollinger + เลขจิตวิทยา ข้ามแนวใกล้สุด 1 ชั้น (เอาแนวที่ 2 เป็นแนวที่ 1) ชั้นที่ 2 ห่างชั้นที่ 1 ≥ ~1.0 ATR หรือ 1.0%
- ข้อมูลล่าช้าตาม Yahoo Finance — ประกอบการตัดสินใจ ไม่ใช่คำแนะนำซื้อขาย
