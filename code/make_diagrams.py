"""Generate the Exercise 8 diagrams and reproducible run outputs."""
import csv, json, math, sys
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT, DATA = ROOT / "diagrams", ROOT / "output"
OUT.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "code"))
from dining_philosophers import DiningPhilosophers
from model_check import explore_naive, explore_ordered


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=180, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def dining_table():
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_aspect("equal"); ax.axis("off")
    pts = []
    for i in range(5):
        a = math.pi / 2 - 2 * math.pi * i / 5
        x, y = 2 * math.cos(a), 2 * math.sin(a)
        pts.append((x, y))
        ax.add_patch(Circle((x, y), .32, fill=False, linewidth=2))
        ax.text(x, y, f"P{i}", ha="center", va="center")
    for i in range(5):
        x, y = (pts[i][0] + pts[(i+1)%5][0]) / 2, (pts[i][1] + pts[(i+1)%5][1]) / 2
        norm = math.hypot(x, y); x, y = x / norm * 1.05, y / norm * 1.05
        ax.add_patch(FancyBboxPatch((x-.16, y-.11), .32, .22, boxstyle="round,pad=.02", fill=False))
        ax.text(x, y, f"F{i}", ha="center", va="center", fontsize=9)
    ax.text(0, 0, "Shared table\nN = 5", ha="center", va="center")
    ax.set_xlim(-2.7,2.7); ax.set_ylim(-2.5,2.6)
    ax.set_title("Dining philosophers and shared forks")
    save(fig, "fig_dining_table")


def wait_cycle():
    fig, ax = plt.subplots(figsize=(6,5)); ax.set_aspect("equal"); ax.axis("off")
    pts=[]
    for i in range(5):
        a=math.pi/2-2*math.pi*i/5; pts.append((1.8*math.cos(a),1.8*math.sin(a)))
    for i,p in enumerate(pts):
        q=pts[(i+1)%5]
        ax.add_patch(Circle(p,.3,fill=False,linewidth=2)); ax.text(*p,f"P{i}",ha="center",va="center")
        ax.add_patch(FancyArrowPatch(p,q,arrowstyle="-|>",mutation_scale=14,connectionstyle="arc3,rad=.2",shrinkA=22,shrinkB=22))
    ax.text(0,0,"P0 → P1 → P2 →\nP3 → P4 → P0",ha="center",va="center")
    ax.set_xlim(-2.5,2.5); ax.set_ylim(-2.3,2.3)
    ax.set_title("Wait-for cycle: naive left-then-right")
    save(fig,"fig_wait_for_cycle")


def order_dag():
    fig, ax=plt.subplots(figsize=(7,3.4)); ax.axis("off")
    xs=[.6,2.1,3.6,5.1,6.6]
    for i,x in enumerate(xs):
        ax.add_patch(Circle((x,1.6),.25,fill=False,linewidth=2)); ax.text(x,1.6,f"F{i}",ha="center",va="center")
        if i<4: ax.add_patch(FancyArrowPatch((x+.28,1.6),(xs[i+1]-.28,1.6),arrowstyle="-|>",mutation_scale=13))
    ax.text(3.6,.65,"Every request moves from a lower ID to a higher ID",ha="center")
    ax.text(3.6,.25,"A strict increasing order cannot form a cycle",ha="center",fontsize=9)
    ax.set_xlim(0,7.2); ax.set_ylim(0,2.1); ax.set_title("Global resource hierarchy")
    save(fig,"fig_resource_order")


def flowchart():
    fig,ax=plt.subplots(figsize=(7,7)); ax.axis("off")
    steps=["Hungry","Wait for FIFO room permit (N-1)","Sort two fork IDs","Acquire lower fork (FIFO)","Acquire higher fork (FIFO)","Eat for finite time","Release both forks and room","Think and repeat"]
    ys=list(range(7,-1,-1))
    for label,y in zip(steps,ys):
        ax.add_patch(FancyBboxPatch((.8,y-.25),5.5,.5,boxstyle="round,pad=.06",fill=False))
        ax.text(3.55,y,label,ha="center",va="center",fontsize=9)
    for y in ys[:-1]:
        ax.add_patch(FancyArrowPatch((3.55,y-.28),(3.55,y-0.72),arrowstyle="-|>",mutation_scale=11))
    ax.set_xlim(0,7); ax.set_ylim(-.7,7.6); ax.set_title("Proposed fair admission and ordered locks")
    save(fig,"fig_proposed_flow")


def simulate():
    sim = DiningPhilosophers(5, eat_seconds=.002, think_seconds=.0005)
    events = sim.run(2, timeout=10)
    base = min(e[4] for e in events)
    meals = {i: [] for i in range(5)}
    starts = {}
    for seq, i, action, pair, stamp in events:
        if action == "eat_start": starts.setdefault(i, []).append((stamp-base, pair))
        elif action == "eat_end":
            start, pair = starts[i].pop(0)
            meals[i].append((start, stamp-base, pair))
    summary = {"philosophers":5,"meals_per_philosopher":2,
               "events":len(events),"meals_completed":sum(sim.meals),
               "per_philosopher":sim.meals,
               "all_completed":sim.meals == [2]*5}
    (DATA/"simulation_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    with (DATA/"simulation_events.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["sequence","philosopher","action","fork_a","fork_b","relative_seconds"])
        for seq,i,action,pair,stamp in events: w.writerow([seq,i,action,*pair,f"{stamp-base:.6f}"])
    fig,ax=plt.subplots(figsize=(8,4))
    for i,items in meals.items():
        for start,end,pair in items: ax.barh(i,end-start,left=start,height=.5)
    ax.set_yticks(range(5),[f"P{i}" for i in range(5)])
    ax.set_xlabel("Elapsed seconds"); ax.set_ylabel("Philosopher")
    ax.set_title("Observed eat intervals in one threaded run")
    ax.grid(axis="x",alpha=.25); save(fig,"fig_meal_timeline")


def main():
    dining_table(); wait_cycle(); order_dag(); flowchart(); simulate()
    a,b=explore_naive(5),explore_ordered(5)
    payload={"naive":{"states":a.states,"transitions":a.transitions,"deadlocks":a.deadlocks},
             "proposed":{"states":b.states,"transitions":b.transitions,"deadlocks":b.deadlocks}}
    (DATA/"model_check.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
