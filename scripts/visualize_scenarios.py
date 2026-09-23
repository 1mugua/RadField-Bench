#!/usr/bin/env python3
"""Render the full scenario library into one self-contained interactive HTML viewer.

Shows, for every scenario: world bounds, obstacles (by material), the true
expected detector count-rate field (log scale), source locations (size ~
strength), robot start pose, and the task goal if any.

Usage:  python scripts/visualize_scenarios.py [output.html]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from radfield_bench.models import Pose2D  # noqa: E402
from radfield_bench.physics import GammaField  # noqa: E402
from radfield_bench.scenario import load_scenario  # noqa: E402

GRID_X = 56
GRID_Y = 42


def quantize(value: float, vmin: float, vmax: float) -> int:
    if vmax <= vmin:
        return 0
    t = (math.log10(value) - vmin) / (vmax - vmin)
    return max(0, min(255, int(round(t * 255))))


def render_scenario_data(path: Path, vmin: float, vmax: float) -> dict:
    scenario = load_scenario(path)
    field = GammaField(scenario)
    bounds = scenario.world
    nx, ny = GRID_X, GRID_Y
    cells: list[int] = []
    for iy in range(ny):
        for ix in range(nx):
            x = bounds.x_min + (ix + 0.5) * (bounds.x_max - bounds.x_min) / nx
            y = bounds.y_min + (iy + 0.5) * (bounds.y_max - bounds.y_min) / ny
            rate = field.expected_detector_cps(Pose2D(x=x, y=y, yaw=0.0))
            cells.append(quantize(max(rate, 1e-6), vmin, vmax))
    meta = scenario.metadata or {}
    task = scenario.task
    return {
        "id": scenario.scenario_id,
        "domain": meta.get("domain", "?"),
        "family": meta.get("family", "?"),
        "difficulty": meta.get("difficulty", "?"),
        "instance": meta.get("instance", "?"),
        "description": meta.get("description", ""),
        "task_type": task.task_type,
        "max_steps": task.max_steps,
        "dose_budget": task.dose_budget,
        "goal": list(task.goal) if task.goal else None,
        "world": [bounds.x_min, bounds.x_max, bounds.y_min, bounds.y_max],
        "obstacles": [
            [o.x_min, o.x_max, o.y_min, o.y_max, o.material] for o in scenario.obstacles
        ],
        "sources": [
            [s.x, s.y, s.reference_cps_at_1m, s.source_id] for s in scenario.sources
        ],
        "start": [scenario.robot.start.x, scenario.robot.start.y, scenario.robot.start.yaw],
        "grid": ",".join(str(v) for v in cells),
    }


def collect_all(scenario_root: Path) -> list[dict]:
    files = sorted(p for p in scenario_root.glob("*/*.yaml"))
    data: list[dict] = []
    # global log scale over every scenario's expected rate
    vmin, vmax = 1e9, -1e9
    for path in files:
        scenario = load_scenario(path)
        field = GammaField(scenario)
        bounds = scenario.world
        for iy in range(GRID_Y):
            for ix in range(GRID_X):
                x = bounds.x_min + (ix + 0.5) * (bounds.x_max - bounds.x_min) / GRID_X
                y = bounds.y_min + (iy + 0.5) * (bounds.y_max - bounds.y_min) / GRID_Y
                rate = field.expected_detector_cps(
                    Pose2D(x=x, y=y, yaw=0.0)
                )
                rate = max(rate, 1e-6)
                vmin = min(vmin, math.log10(rate))
                vmax = max(vmax, math.log10(rate))
    for path in files:
        data.append(render_scenario_data(path, vmin, vmax))
    return data, vmin, vmax


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RadField-Bench 场景库浏览器</title>
<style>
  body { margin:0; font-family:system-ui,'Microsoft YaHei',sans-serif; background:#0f172a; color:#e2e8f0; }
  header { padding:14px 20px; background:#1e293b; border-bottom:1px solid #334155; }
  header h1 { margin:0; font-size:18px; color:#f8fafc; }
  header p { margin:4px 0 0; font-size:12px; color:#94a3b8; }
  .layout { display:flex; min-height:calc(100vh - 64px); }
  aside { width:280px; flex:0 0 280px; border-right:1px solid #334155; overflow-y:auto; padding:10px; background:#111c2e; }
  .domain { margin-bottom:8px; }
  .domain-title { font-weight:700; font-size:13px; color:#7dd3fc; padding:6px 4px; cursor:pointer; display:flex; justify-content:space-between; }
  .domain-count { color:#64748b; font-weight:400; }
  .family { margin:2px 0 2px 8px; }
  .family-title { font-size:12px; font-weight:600; color:#cbd5e1; padding:4px; }
  .diff-row { display:flex; gap:4px; padding:2px 0 2px 12px; }
  .diff-btn { flex:1; font-size:11px; padding:3px 0; border-radius:4px; border:1px solid #334155; background:#1e293b; color:#94a3b8; cursor:pointer; text-align:center; }
  .diff-btn:hover { border-color:#64748b; color:#e2e8f0; }
  .diff-btn.sel { background:#0ea5e9; border-color:#0ea5e9; color:#fff; }
  main { flex:1; padding:16px 20px; overflow:auto; }
  #meta { margin-bottom:10px; font-size:13px; }
  #meta .id { font-size:16px; font-weight:700; color:#f8fafc; }
  #meta .desc { color:#94a3b8; margin-top:2px; }
  #svgbox { background:#0b1220; border:1px solid #334155; border-radius:10px; padding:12px; display:inline-block; }
  svg { display:block; }
  .legend { margin-top:12px; font-size:12px; color:#cbd5e1; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .bar { width:260px; height:12px; border-radius:3px; background:linear-gradient(to right,#1d4ed8,#0ea5e9,#22c55e,#facc15,#ef4444,#a855f7); }
  .chip { display:inline-flex; align-items:center; gap:6px; margin-left:14px; }
  .sw { width:14px; height:14px; display:inline-block; border-radius:3px; }
  .hint { color:#64748b; margin-left:auto; }
</style>
</head>
<body>
<header>
  <h1>RadField-Bench 业务领域场景库 · 可视化浏览器</h1>
  <p>真实期望计数率场（对数色标，全局共享）· 障碍物按材料着色 · 圆点=放射源（大小∝强度）· 绿三角=起点 · 金星=任务终点</p>
</header>
<div class="layout">
  <aside id="nav"></aside>
  <main>
    <div id="meta"></div>
    <div id="svgbox"><svg id="scene" width="820" height="620"></svg></div>
    <div class="legend">
      <span>期望计数率 (cps，对数)</span>
      <div class="bar"></div>
      <span id="leglo">--</span>
      <span>→</span>
      <span id="leghi">--</span>
      <span class="chip"><span class="sw" style="background:#94a3b8"></span>混凝土</span>
      <span class="chip"><span class="sw" style="background:#475569"></span>钢材</span>
      <span class="chip"><span class="sw" style="background:#22c55e"></span>起点</span>
      <span class="chip"><span class="sw" style="background:#eab308;border-radius:50%"></span>终点</span>
      <span class="chip"><span class="sw" style="background:#ef4444;border-radius:50%"></span>放射源</span>
      <span class="hint">来源：scenarios/*.yaml 真值场（开发/文档用途）</span>
    </div>
  </main>
</div>
<script>
const SCENARIOS = __DATA__;
const VMIN = __VMIN__;
const VMAX = __VMAX__;
const DOMAINS = __DOMAINS__;

function colorFor(t) {
  const stops = [[0,[29,78,216]],[0.25,[14,165,233]],[0.45,[34,197,94]],[0.65,[250,204,21]],[0.85,[239,68,68]],[1,[168,85,247]]];
  for (let i=1;i<stops.length;i++) {
    if (t <= stops[i][0]) {
      const [t0,c0] = stops[i-1], [t1,c1] = stops[i];
      const k = (t-t0)/(t1-t0);
      return `rgb(${Math.round(c0[0]+(c1[0]-c0[0])*k)},${Math.round(c0[1]+(c1[1]-c0[1])*k)},${Math.round(c0[2]+(c1[2]-c0[2])*k)})`;
    }
  }
  return 'rgb(168,85,247)';
}

function worldAspect(s){ const [x0,x1,y0,y1]=s.world; return (x1-x0)/(y1-y0); }

function renderScene(s){
  const svg = document.getElementById('scene');
  const W=820, H=620;
  const [x0,x1,y0,y1]=s.world;
  const aw=W/(x1-x0), ah=H/(y1-y0), a=Math.min(aw,ah)*0.96;
  const ox=(W-(x1-x0)*a)/2, oy=(H-(y1-y0)*a)/2;
  const X=x=>ox+(x-x0)*a, Y=y=>oy+(H-(y-y0)*a);
  let html='';
  // heatmap
  const cells=s.grid.split(',');
  const ny=42, nx=56;
  const cw=(x1-x0)/nx*a, ch=(y1-y0)/ny*a;
  for(let iy=0;iy<ny;iy++){
    for(let ix=0;ix<nx;ix++){
      const v=parseInt(cells[iy*nx+ix],10);
      const xg=x0+(ix+0.5)*(x1-x0)/nx, yg=y0+(iy+0.5)*(y1-y0)/ny;
      const r=parseInt(v,10)/255;
      html+=`<rect x="${X(xg)-cw/2}" y="${Y(yg)-ch/2}" width="${cw+0.3}" height="${ch+0.3}" fill="${colorFor(r)}" opacity="0.9"/>`;
    }
  }
  // obstacles
  for(const [a0,a1,b0,b1,m] of s.obstacles){
    const fill = m==='concrete' ? '#94a3b8' : '#475569';
    html+=`<rect x="${X(a0)}" y="${Y(b1)}" width="${(a1-a0)*a}" height="${(b1-b0)*a}" fill="${fill}" stroke="#0b1220" stroke-width="1"/>`;
  }
  // sources
  for(const [sx,sy,str,id] of s.sources){
    const r=6+Math.sqrt(str)*0.55;
    html+=`<circle cx="${X(sx)}" cy="${Y(sy)}" r="${r}" fill="#ef4444" stroke="#fecaca" stroke-width="1.5" opacity="0.92"/>`;
    html+=`<title>${id} strength=${str} cps@1m</title>`;
  }
  // goal
  if(s.goal){
    const [gx,gy]=s.goal;
    html+=`<path d="M ${X(gx)} ${Y(gy)-10} L ${X(gx)+4.5} ${Y(gy)+7} L ${X(gx)-4.5} ${Y(gy)+7} Z" fill="#eab308" stroke="#0b1220" stroke-width="1"/>`;
  }
  // start
  const [px,py,pyaw]=s.start;
  const len=13;
  const ex=px+Math.cos(pyaw)*len, ey=py+Math.sin(pyaw)*len;
  const bx=px-Math.cos(pyaw+Math.PI/2.6)*8, by=py-Math.sin(pyaw+Math.PI/2.6)*8;
  const cx=px-Math.cos(pyaw-Math.PI/2.6)*8, cy=py-Math.sin(pyaw-Math.PI/2.6)*8;
  html+=`<path d="M ${X(ex)} ${Y(ey)} L ${X(bx)} ${Y(by)} L ${X(cx)} ${Y(cy)} Z" fill="#22c55e" stroke="#0b1220" stroke-width="1"/>`;
  svg.innerHTML=html;
  // meta
  document.getElementById('meta').innerHTML =
    `<div class="id">${s.id}</div><div class="desc">${s.description || ''} · 任务:${s.task_type} · 步数上限:${s.max_steps} · 暴露预算:${s.dose_budget}${s.goal?' · 终点:('+s.goal[0].toFixed(1)+','+s.goal[1].toFixed(1)+')':''}</div>`;
  document.getElementById('leglo').textContent='10^'+VMIN.toFixed(1);
  document.getElementById('leghi').textContent='10^'+VMAX.toFixed(1);
}

function buildNav(selKey){
  const nav=document.getElementById('nav');
  let html='';
  for(const dom of DOMAINS){
    html+=`<div class="domain"><div class="domain-title">${dom.name} <span class="domain-count">${dom.count} 场景</span></div>`;
    for(const fam of dom.families){
      html+=`<div class="family"><div class="family-title">${fam.name}</div>`;
      for(const diff of Object.keys(fam.difficulties)){
        const key=fam.difficulties[diff].key;
        html+=`<div class="diff-row"><button class="diff-btn ${key===selKey?'sel':''}" onclick="renderSceneById('${key}')">${diff}</button></div>`;
      }
      html+=`</div>`;
    }
    html+=`</div>`;
  }
  nav.innerHTML=html;
}

function renderSceneById(key){
  const s=SCENARIOS.find(x=>x.id===key);
  if(!s) return;
  renderScene(s);
  buildNav(key);
}

// init: default to the first scenario
if (SCENARIOS.length) {
  renderSceneById(SCENARIOS[0].id);
}
</script>
</body>
</html>
"""


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    scenario_root = repo / "scenarios"
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "scenarios" / "visualization.html"

    data, vmin, vmax = collect_all(scenario_root)

    # rebuild domain navigation tree cleanly
    domains: list[dict] = []
    domain_map: dict[str, dict] = {}
    for item in data:
        dname = item["domain"]
        if dname not in domain_map:
            domain_map[dname] = {"name": dname, "families": {}, "count": 0}
        d = domain_map[dname]
        d["count"] += 1
        fname = item["family"]
        if fname not in d["families"]:
            d["families"][fname] = {"name": fname, "difficulties": {}}
        d["families"][fname]["difficulties"][item["difficulty"]] = {"key": item["id"]}
    for dname in sorted(domain_map):
        d = domain_map[dname]
        domains.append({
            "name": dname,
            "count": d["count"],
            "families": [{"name": f, "difficulties": d["families"][f]["difficulties"]} for f in sorted(d["families"])],
        })

    html = (
        HTML_TEMPLATE
        .replace("__DATA__", json.dumps(data, ensure_ascii=False))
        .replace("__VMIN__", repr(vmin))
        .replace("__VMAX__", repr(vmax))
        .replace("__DOMAINS__", json.dumps(domains, ensure_ascii=False))
    )
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {len(data)} scenarios -> {out_path} ({out_path.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
