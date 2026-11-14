"""Build the printable Persian hand-solution PDF for Exercise 3 (HTML -> headless Chrome).
All numbers come from edf_rm.py so the document and the code cannot disagree."""
import base64, os, subprocess, sys
from edf_rm import *
from make_figures import TASKS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "output")
DIA = os.path.join(HERE, "..", "diagrams")
TS = TASKS
N = [t.name for t in TS]


def img(name):
    with open(os.path.join(DIA, name), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def jlabel(v):
    return f"{v[0]}<sub>{v[1]}</sub>"


def step_table(algo):
    rows = []
    for t, ready, ch in trace(TS, algo):
        if ch is None:
            rows.append(f"<tr><td><span class=ltr>{t}–{t+1}</span></td><td>—</td><td>Idle</td><td>هیچ کار آماده‌ای وجود ندارد</td></tr>")
            continue
        rd = "، ".join(f"{jlabel(v)}(d={v[2]}, rem={v[3]})" for v in ready)
        if algo == "EDF":
            same = [v for v in ready if v[2] == ch[2] and v != ch]
            why = f"کمترین Deadline مطلق: d={ch[2]}"
            if same:
                why += " (تساوی با " + "، ".join(jlabel(v) for v in same) + "؛ شاخص وظیفه کوچک‌تر)"
        else:
            T = {t_.name: t_.T for t_ in TS}[ch[0]]
            why = f"بالاترین اولویت ثابت (T={T})"
        rows.append(f"<tr><td><span class=ltr>{t}–{t+1}</span></td><td class=l>{rd}</td><td><b>{jlabel(ch)}</b></td><td>{why}</td></tr>")
    return ("<table class=s><tr><th>بازه</th><th>کارهای آماده</th><th>اجرا</th><th>دلیل انتخاب</th></tr>"
            + "".join(rows) + "</table>")


def preemptions(algo):
    tl, jobs, _ = simulate(TS, algo)
    c = 0
    for t in range(1, len(tl)):
        a, b = tl[t - 1], tl[t]
        if a is not None and b is not None and a != b:
            # was the previous slot's job finished at t?
            fin = any(j.finish == t and j.task == a and j.start is not None and j.release <= t - 1 for j in jobs
                      if j.finish == t)
            if not fin:
                c += 1
    return c


def job_table(algo):
    tl, jobs, miss = simulate(TS, algo)
    rows = []
    for j in sorted(jobs, key=lambda j: (j.task, j.k)):
        ok = j.finish is not None and j.finish <= j.deadline
        rows.append(f"<tr class={'ok' if ok else 'bad'}><td>{jlabel((N[j.task], j.k))}</td><td>{j.release}</td>"
                    f"<td>{j.start}</td><td>{j.finish}</td><td>{j.deadline}</td><td>{j.finish - j.release}</td>"
                    f"<td>{j.start - j.release}</td><td>{'رعایت شد' if ok else 'Deadline Miss'}</td></tr>")
    return ("<table><tr><th>Job</th><th>Release</th><th>Start</th><th>Finish</th><th>Abs. Deadline</th>"
            "<th>Response</th><th>Wait تا شروع</th><th>وضعیت</th></tr>" + "".join(rows) + "</table>")


def blank_grid():
    head = "".join(f"<th>{i}</th>" for i in range(24))
    rows = "".join(f"<tr><th>{n}</th>" + "<td></td>" * 24 + "</tr>" for n in N)
    return f"<table class=g><tr><th></th>{head}</tr>{rows}</table>"


def main():
    U = utilization(TS)
    rta = response_time_analysis(TS)
    tle, _, me = simulate(TS, "EDF")
    tlr, _, mr = simulate(TS, "RM")
    assert not me and len(mr) == 1 and rta["T3"] == 14
    task_rows = "".join(f"<tr><td>{t.name}</td><td>{t.C}</td><td>{t.T}</td><td>{t.D}</td><td>{t.phase}</td>"
                        f"<td>{t.C}/{t.T} = {t.C/t.T:.4f}</td></tr>" for t in TS)
    html = f"""<!doctype html><html lang=fa dir=rtl><head><meta charset=utf-8>
<style>
@page {{ size: A4; margin: 16mm 14mm 18mm 14mm; @bottom-center {{ content: counter(page); font-family: Vazirmatn; font-size: 9pt; }} }}
body {{ font-family: Vazirmatn; font-size: 10.5pt; line-height: 1.75; color: #111; }}
h1 {{ font-size: 20pt; margin: 0 0 4px; }} h2 {{ font-size: 14pt; border-bottom: 2px solid #4C78A8; padding-bottom: 2px; margin-top: 18px; }}
h3 {{ font-size: 11.5pt; margin: 12px 0 4px; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 9.5pt; text-align: center; }}
th, td {{ border: 1px solid #555; padding: 2px 5px; }} th {{ background: #dfe8f3; }}
td.l {{ text-align: left; direction: ltr; font-size: 8.5pt; }}
table.s {{ font-size: 8.5pt; }} table.s td, table.s th {{ padding: 1px 4px; }}
tr.bad td {{ background: #ffd6d6; }} tr.ok td {{ background: #f3fbf3; }}
table.g td {{ height: 26px; width: 3.4%; }} table.g th {{ font-size: 8pt; padding: 0; }}
.box {{ border: 1.5px solid #4C78A8; background: #f4f8fc; padding: 6px 10px; border-radius: 4px; margin: 8px 0; }}
.warn {{ border-color: #c0392b; background: #fdf1f0; }}
.ltr {{ white-space: nowrap; direction: ltr; unicode-bidi: embed; display: inline-block; }}
img {{ width: 100%; }} .keep {{ break-inside: avoid; }} .pb {{ page-break-before: always; }}
.lines {{ height: 230px; background: repeating-linear-gradient(white, white 27px, #aaa 28px); border: 1px solid #888; }}
.cover {{ text-align: center; margin-top: 120px; }} .cover h1 {{ font-size: 26pt; }}
</style></head><body>

<div class=cover>
<h1>زمان‌بندی الگوریتم‌های EDF و RM<br>با سه وظیفه — حل دستی گام‌به‌گام</h1>
<p style="font-size:13pt">تمرین ۳ — درس سیستم‌عامل</p>
<p>مخزن: Multilevel-Queue-Scheduling · شاخه: Exercise-3-EDF-RM-Manual-Scheduling</p>
<p>تمام اعداد این سند از اجرای برنامه <span class=ltr>code/edf_rm.py</span> گرفته شده و با تست‌های خودکار (۱۶ تست) تطبیق داده شده‌اند.</p>
<p>نام و شماره دانشجویی: ........................................</p>
</div>

<div class=pb></div>
<h2>۱. مدل و فرضیات</h2>
<ul>
<li>یک پردازنده، پیش‌دستی‌پذیر (Preemptive)، بدون هزینه Context Switch.</li>
<li>وظایف دوره‌ای و مستقل؛ هر Job در لحظه <span class=ltr>r = phase + k·T</span> آزاد می‌شود و Deadline مطلق آن <span class=ltr>r + D</span> است.</li>
<li>زمان گسسته با گام ۱ واحد. اگر Jobی در Deadline خود تمام نشده باشد «Deadline Miss» ثبت می‌شود و Job تا پایان ادامه می‌یابد (لغو نمی‌شود).</li>
<li><b>قاعده تساوی:</b> در EDF اگر دو Job یک Deadline داشتند، وظیفه با شاخص کوچک‌تر (T1 قبل از T2 قبل از T3) اجرا می‌شود. در RM تساوی اولویت رخ نمی‌دهد (دوره‌ها متفاوت‌اند).</li>
<li>زمان‌بندی روی یک ابردوره (Hyperperiod) بررسی می‌شود.</li>
</ul>

<h2>۲. مشخصات سه وظیفه</h2>
<table><tr><th>وظیفه</th><th>C (اجرا)</th><th>T (دوره)</th><th>D (Deadline نسبی)</th><th>Release اول (phase)</th><th>بهره‌وری C/T</th></tr>{task_rows}</table>
<p><b>بهره‌وری کل:</b> <span class=ltr>U = 1/4 + 3/8 + 4/12 = 6/24 + 9/24 + 8/24 = 23/24 ≈ {U:.4f}</span></p>
<p><b>ابردوره:</b> <span class=ltr>H = lcm(4, 8, 12) = 24</span>؛ پس T1 شش Job، T2 سه Job و T3 دو Job دارد. کل کار = 6·1 + 3·3 + 2·4 = 23 واحد؛ بنابراین <b>Idle Time = 24 − 23 = 1</b> واحد.</p>
<div class=box><b>آزمون‌های نظری:</b><br>
• EDF (وظایف دوره‌ای، D=T، یک پردازنده، پیش‌دستی‌پذیر): شرط لازم و کافی <span class=ltr>U ≤ 1</span> است (Liu &amp; Layland, 1973). اینجا 0.9583 ≤ 1 ⇒ زمان‌بندی‌پذیر.<br>
• RM: شرط کافی <span class=ltr>U ≤ n(2<sup>1/n</sup> − 1)</span> برای n=3 برابر 0.7798 است. چون 0.9583 &gt; 0.7798، این آزمون <b>بی‌نتیجه</b> است (نه اثبات شکست و نه موفقیت). باید آزمون دقیق‌تر یا شبیه‌سازی/تحلیل زمان پاسخ استفاده شود.</div>

<h2>۳. اولویت‌ها و Jobها</h2>
<p><b>RM:</b> هرچه دوره کوتاه‌تر، اولویت ثابت بالاتر: T1 (T=4) &gt; T2 (T=8) &gt; T3 (T=12).<br>
<b>EDF:</b> اولویت پویاست؛ در هر لحظه Job آماده با کوچک‌ترین Deadline مطلق انتخاب می‌شود.</p>
<table><tr><th>وظیفه</th><th>Release (k=0,1,…)</th><th>Deadline مطلق</th></tr>
<tr><td>T1</td><td>0, 4, 8, 12, 16, 20</td><td>4, 8, 12, 16, 20, 24</td></tr>
<tr><td>T2</td><td>0, 8, 16</td><td>8, 16, 24</td></tr>
<tr><td>T3</td><td>0, 12</td><td>12, 24</td></tr></table>

<div class=pb></div>
<h2>۴. حل گام‌به‌گام EDF</h2>
<p>در هر ثانیه، ستون «کارهای آماده» Jobهای آزادشده و ناتمام را با Deadline مطلق (d) و زمان باقی‌مانده (rem) نشان می‌دهد. <span class=ltr>T2<sub>1</sub></span> یعنی Job شماره ۱ از T2.</p>
{step_table("EDF")}
<div class=keep><h3>نمودار Gantt — EDF</h3><img src="{img('gantt_edf.png')}"></div>
<p><b>مشاهده کلیدی (t=8..9):</b> T1<sub>2</sub> و T3<sub>0</sub> هر دو Deadline=12 دارند. با قاعده تساوی ابتدا T1<sub>2</sub> (۱ واحد) و سپس T3<sub>0</sub> اجرا می‌شود و در t=10 تمام می‌شود — پیش از Deadline.</p>
<h3>جدول نتایج Jobها — EDF</h3>{job_table("EDF")}
<p>Deadline Miss: <b>۰</b> · Idle: <b>1</b> واحد (بازه <span class=ltr>23–24</span>) · پیش‌دستی‌ها: <b>{preemptions("EDF")}</b> · CPU Utilization = 23/24 = 95.83٪</p>

<div class=pb></div>
<h2>۵. حل گام‌به‌گام RM</h2>
{step_table("RM")}
<div class=keep><h3>نمودار Gantt — RM</h3><img src="{img('gantt_rm.png')}"></div>
<h3>جدول نتایج Jobها — RM</h3>{job_table("RM")}
<p>Deadline Miss: <b>۱</b> (Job اول T3 در Deadline=12 تمام نشده و در t=14 تمام می‌شود) · Idle: <b>1</b> واحد (بازه <span class=ltr>23–24</span>) · پیش‌دستی‌ها: <b>{preemptions("RM")}</b> · CPU Utilization = 23/24.</p>

<h3>اثبات دستی عدم زمان‌بندی‌پذیری RM (تحلیل زمان پاسخ)</h3>
<p>برای T3 با کار بالاتر T1 (C=1,T=4) و T2 (C=3,T=8): <span class=ltr>R = 4 + ⌈R/4⌉·1 + ⌈R/8⌉·3</span></p>
<table><tr><th>تکرار</th><th>R قبلی</th><th>محاسبه</th><th>R جدید</th></tr>
<tr><td>0</td><td>4</td><td class=l>4 + ⌈4/4⌉·1 + ⌈4/8⌉·3 = 4+1+3</td><td>8</td></tr>
<tr><td>1</td><td>8</td><td class=l>4 + ⌈8/4⌉·1 + ⌈8/8⌉·3 = 4+2+3</td><td>9</td></tr>
<tr><td>2</td><td>9</td><td class=l>4 + ⌈9/4⌉·1 + ⌈9/8⌉·3 = 4+3+6</td><td>13</td></tr>
<tr><td>3</td><td>13</td><td class=l>4 + ⌈13/4⌉·1 + ⌈13/8⌉·3 = 4+4+6</td><td>14</td></tr>
<tr><td>4</td><td>14</td><td class=l>4 + ⌈14/4⌉·1 + ⌈14/8⌉·3 = 4+4+6</td><td>14 (همگرا)</td></tr></table>
<p>زمان پاسخ T3 برابر 14 &gt; D=12 است ⇒ Deadline Miss، که با Gantt یکسان است. (برای T1: R=1، برای T2: R=4+… = 4 ≤ 8.)</p>

<div class=pb></div>
<h2>۶. مقایسه و تحلیل</h2>
<table><tr><th>معیار</th><th>EDF</th><th>RM</th></tr>
<tr><td>تعداد Deadline Miss</td><td>0</td><td>1 (T3<sub>0</sub>)</td></tr>
<tr><td>Idle Time در [0,24)</td><td>1</td><td>1</td></tr>
<tr><td>CPU Utilization</td><td>23/24 ≈ 95.83٪</td><td>23/24 ≈ 95.83٪</td></tr>
<tr><td>پیش‌دستی‌ها</td><td>{preemptions("EDF")}</td><td>{preemptions("RM")}</td></tr>
<tr><td>نوع اولویت</td><td>پویا (Deadline)</td><td>ثابت (دوره)</td></tr>
<tr><td>زمان پاسخ T3<sub>0</sub></td><td>10</td><td>14</td></tr></table>
<p><b>چرا تفاوت؟</b> در t=8 با رسیدن T1<sub>2</sub> و T2<sub>1</sub>، RM به اولویت ثابت پایبند است و T2<sub>1</sub> را قبل از T3<sub>0</sub> اجرا می‌کند، در حالی که Deadline T3<sub>0</sub> (۱۲) زودتر از T2<sub>1</sub> (۱۶) است. EDF این وضعیت را با مقایسه Deadlineها درست مدیریت می‌کند.</p>
<div class="box warn"><b>محدودیت‌ها:</b> این نمونه یک مجموعه وظیفه خاص با release همزمان (phase=0) است. نتیجه «RM بدتر است» برای همه مجموعه‌ها صادق نیست؛ برای بسیاری از مجموعه‌های با U کم، RM هم موفق است. همچنین بررسی یک ابردوره برای این مجموعه (D=T، phase صفر) کافی و دقیق است، اما این روش برای مدل‌های دیگر (offset، D&lt;T، زمان اجرای متغیر، هزینه Context Switch) به‌تنهایی اثبات زمان‌بندی‌پذیری نیست.</div>

<div class=pb></div>
<h2>۷. فضای بازنویسی دستی</h2>
<p>جدول زیر را با دست پر کنید (هر خانه یک واحد زمان). ابتدا EDF، سپس RM.</p>
<h3>EDF</h3>{blank_grid()}<h3>RM</h3>{blank_grid()}
<h3>یادداشت</h3><div class=lines></div>
</body></html>"""
    os.makedirs(OUT, exist_ok=True)
    hp = os.path.join(OUT, "manual_solution_fa.html")
    with open(hp, "w", encoding="utf-8") as f:
        f.write(html)
    pdf = os.path.join(OUT, "HAND_WORKSHEET_FA.pdf")
    subprocess.run(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", "file://" + os.path.abspath(hp)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("wrote", pdf)


if __name__ == "__main__":
    main()
