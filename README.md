# CS2 Demo Local Review & 2D Replay

> Local CS2 (Counter-Strike 2) demo parsing, Dust2 coordinate mapping, deterministic rule-based review, 2D web replay, a sandbox tactics board, and lightweight 5-person room collaboration. No LLM, no AstrBot, no database.

[English](#english) · [中文](#中文)

---

## English

### What it is

A self-hosted toolkit that turns local `.dem` files into:

- A CLI for parsing, deterministic rule analysis, and a Chinese review report.
- A FastAPI + vanilla HTML/CSS/JS + Canvas 2D replay web page.
- A sandbox tactics board (move tokens, draw arrows/text/brush, plan utility throws).
- Optional 5-person rooms synced over WebSocket, with optional public HTTPS share links.

Scope is intentionally narrow: **Dust2 only**, deterministic findings (no LLM), and incremental features over a refactor.

### Requirements

- Python 3.12 (the project is developed against a conda env named `cs2demo`).
- A local CS2 `.dem` file. **Demo files are NOT included in this repo** — they are large binaries (often > 100 MB) and may contain match/player data, so `samples/demos/` and `*.dem` are git-ignored. Drop your own `.dem` into `samples/demos/` before running.
- Optional, only for public room sharing: a locally installed [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/). The project never auto-downloads or installs it.

### Setup

```bash
conda create -n cs2demo python=3.12 -y
conda activate cs2demo
python -m pip install -r requirements.txt
```

You can also run without activating the env:

```bash
conda run -n cs2demo python -m cs2demo.cli parse samples/demos/<your_demo>.dem
```

### Quick start

```bash
# 1. Parse a demo
conda run -n cs2demo python -m cs2demo.cli parse samples/demos/<your_demo>.dem

# 2. Rule analysis + Chinese report
conda run -n cs2demo python -m cs2demo.cli analyze samples/demos/<your_demo>.dem
conda run -n cs2demo python -m cs2demo.cli report  samples/demos/<your_demo>.dem

# 3. Export web replay data
conda run -n cs2demo python -m cs2demo.cli export-replay samples/demos/<your_demo>.dem

# 4. Start the 2D replay web app, then open http://127.0.0.1:8000
conda run -n cs2demo python -m cs2demo.server
```

### Features

- **CLI**: `parse`, `analyze`, `report`, `export-replay`, `inspect-events`, `render-kills`.
- **Deterministic review**: trade failures, entry success/failure, stall rounds, post-plant losses — every finding carries evidence, no LLM.
- **2D replay**: round selection, prev/next round, ±5s seek, play/pause, timeline scrub, finding jump, event markers, health bars, names, yaw arrows, fine-grained utility trajectory/effect toggles.
- **Map viewport**: wheel zoom, drag pan, Fit/Reset, with click/hit-test inverse-transformed back to radar coordinates so overlays stay aligned.
- **Sandbox tactics board**: drag tokens, arrows, text notes, brush strokes, eraser, laser pointer, plan utility throws (smoke/flash/HE/molotov), play/pause planned effects, return to pause point, resume the demo, and save plans as JSON.
- **Rooms (≤ 5 people)**: create a room from the current demo/round/tick, sync playback and sandbox edits over WebSocket. You can switch demos inside a room without recreating it. Room state lives only in `outputs/rooms/*.json` and never pollutes the original replay shards.
- **Analysis filters**: a local-only view preference (side / player / finding type / severity / map overlay mode) that is never written to room state.

### Public room sharing (optional)

By default the server binds `127.0.0.1` and is local-only. To let teammates outside your LAN join like a normal web page, use a public HTTPS tunnel:

```bash
conda run -n cs2demo python -m cs2demo.server --host 127.0.0.1 --port 8000 --tunnel cloudflared
```

This starts a locally installed Cloudflare quick tunnel and resolves a `https://xxxxx.trycloudflare.com` URL; the share dialog then offers `https://xxxxx.trycloudflare.com/r/{room_code}`. You can also set a base URL manually via `--public-url https://example.com` or `CS2PLUGIN_PUBLIC_BASE_URL`. Config precedence: CLI args → env vars → `config/app_config.json` → defaults.

> **Security warning.** A public tunnel exposes the whole web/WebSocket service to the internet, and this service currently has **no authentication, authorization, or rate limiting**. Anyone with the link can create rooms, trigger demo parsing, and write room state. Only enable a tunnel on a trusted network and tear it down when you are done. Never treat `http://127.0.0.1:8000/...` or `http://192.168.x.x:8000/...` as a real share link for teammates.

### What this project does NOT do

No LLM, no AstrBot integration, no account/login, no room passwords, no managed public deployment platform, no multi-map support (Dust2 only), no 3D, no parser rewrite, no React migration. Sandbox/room data is kept strictly isolated from the original demo replay data.

### Coordinate mapping (Dust2)

```python
img_x = (x - pos_x) / scale
img_y = (pos_y - y) / scale
```

Map config comes from `assets/maps/de_dust2/de_dust2.txt` and `assets/maps/de_dust2/de_dust2_radar.png`.

### Project layout

```text
cs2demo/        Python package: CLI, parser, analysis, replay export, FastAPI server, web frontend
config/         utility_effects.json, players.yaml, app_config.json (server/share config)
assets/         Dust2 radar image + map config
samples/demos/  put your own .dem here (git-ignored)
outputs/        generated artifacts (git-ignored)
docs/           project status, structure, and update logs
scripts/        demo field inspection helper
```

See `docs/` for detailed status, structure, and the update log.

---

## 中文

### 简介

一个本地自托管工具，把本地 CS2 `.dem` 文件变成：

- 解析、确定性规则复盘分析和中文报告的 CLI。
- FastAPI + 原生 HTML/CSS/JS + Canvas 2D 的回放网页。
- sandbox 战术推演板（拖 token、画箭头/文字/画笔、规划道具投掷）。
- 可选的 5 人 WebSocket 房间协作，以及可选的公网 HTTPS 分享链接。

范围刻意收窄：**只支持 Dust2**、确定性 findings（不调用 LLM）、优先增量而非重构。

### 运行环境

- Python 3.12（项目使用名为 `cs2demo` 的 conda 环境开发）。
- 本地 CS2 `.dem` 文件。**本仓库不包含任何 demo 文件** —— demo 是大体积二进制（常 > 100 MB）且可能含比赛/玩家数据，因此 `samples/demos/` 和 `*.dem` 已被 git 忽略。运行前请把你自己的 `.dem` 放进 `samples/demos/`。
- 仅公网房间分享时可选：本机已安装的 [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)。项目不会自动下载或安装它。

### 安装

```bash
conda create -n cs2demo python=3.12 -y
conda activate cs2demo
python -m pip install -r requirements.txt
```

也可以不激活环境直接运行：

```bash
conda run -n cs2demo python -m cs2demo.cli parse samples/demos/<你的demo>.dem
```

### 字段检查

如果 demoparser2 字段和预期不同，先运行：

```bash
conda run -n cs2demo python -m cs2demo.cli inspect-events samples/demos/<你的demo>.dem
```

用于打印 demoparser2 可用事件、关键道具事件字段和 `parse_grenades()` projectile 类型计数，避免硬猜字段。

### 解析 demo

```bash
conda run -n cs2demo python -m cs2demo.cli parse samples/demos/<你的demo>.dem
```

默认输出到 `outputs/`：`header.json`、`players.json`、`rounds.json`、`events.jsonl`、`ticks.parquet`（失败时写 `ticks.csv`）、`summary.json`。`summary.json` 包含 `match_header`、`players`、`rounds`、`player_stats`、`key_events`。

### 规则分析

```bash
conda run -n cs2demo python -m cs2demo.cli analyze samples/demos/<你的demo>.dem
```

默认输出 `outputs/findings.json` 和 `outputs/player_metrics.json`。当前 `config/players.yaml` 为空时，分析范围默认是 T/CT 双方；所有 finding 都包含 evidence，不调用 LLM。

### 中文报告

```bash
conda run -n cs2demo python -m cs2demo.cli report samples/demos/<你的demo>.dem
```

报告包含比赛概览、基础数据、Top 5 复盘回合、没补枪问题、突破成功/失败、便秘回合和包后失败回合。

### 2D 回放网页

```bash
conda run -n cs2demo python -m cs2demo.server
```

打开 `http://127.0.0.1:8000`。网页会读取对应 demo 的输出，生成 `outputs/web/{demo_id}/replay.json` 和按回合切分的 replay 数据。支持 round 选择、上一/下一回合、前进/后退 5 秒、播放/暂停、时间轴拖动、finding 跳转、事件 marker、人物血条/名字/朝向开关、细粒度道具轨迹/效果开关，以及暂停后进入 sandbox 拖 token、画箭头、添加文本、画笔涂鸦、橡皮擦删除 annotation、激光笔指示、点击 token 选择道具并投掷、播放/暂停推演效果、回到暂停点、恢复播放 demo 并保存推演方案 JSON；创建房间后这些 replay / sandbox 操作可通过 WebSocket 在 5 人以内同步。

当前页面采用 100vh 战术板布局：顶部只放 demo/round/mode/status；地图是主视觉，右侧只保留当前对象和 sandbox 上下文 inspector；播放控制和 marker 紧凑贴在地图下方；Findings、Utilities、Players、Sandbox Objects、Settings、Legend 等长内容放在可折叠底部 tabs 内滚动。

地图支持统一 viewport：鼠标滚轮缩放、拖拽平移、Zoom In/Out、Fit Map、Reset View。前端先使用 demo 导出的 radar 坐标，再通过 viewport 转成 canvas screen 坐标；点击、命中检测和 sandbox 落点会反变换回 radar 坐标，因此缩放/平移后 token、道具轨迹、烟雾 timer、箭头和文字仍保持对齐。

#### 多人房间、公网分享与分析筛选

网页顶部的“创建房间”会基于当前 demo/round/tick 创建一个 URL-safe 房间码，并把房间状态写到 `outputs/rooms/{room_code}.json`。房间默认仍可本地使用；如果要让不在同一局域网的队友像普通网页一样进入，推荐使用公网 HTTPS 分享方式：

```bash
conda run -n cs2demo python -m cs2demo.server --host 127.0.0.1 --port 8000 --tunnel cloudflared
```

`--tunnel cloudflared` 会启动本机已安装的 Cloudflare quick tunnel，自动解析 `https://xxxxx.trycloudflare.com`，创建房间后分享弹窗会给出 `https://xxxxx.trycloudflare.com/r/{room_code}`。项目不会自动下载或安装 cloudflared；如果未安装，server 会继续以本地模式运行，并在 `/api/share/status` 和前端显示“当前链接只在本机可用”的警告。

也可以手动指定公网 base URL：

```bash
conda run -n cs2demo python -m cs2demo.server --host 127.0.0.1 --port 8000 --public-url https://example.com
```

或使用环境变量：

```bash
CS2PLUGIN_PUBLIC_BASE_URL=https://example.com conda run -n cs2demo python -m cs2demo.server
```

支持的 server 配置入口包括 CLI 参数 `--host`、`--port`、`--public-url`、`--tunnel cloudflared`，环境变量 `CS2PLUGIN_HOST`、`CS2PLUGIN_PORT`、`CS2PLUGIN_PUBLIC_BASE_URL`、`CS2PLUGIN_TUNNEL`，以及 `config/app_config.json`；优先级为 CLI 参数、环境变量、配置文件、默认值。不要把 `http://127.0.0.1:8000/r/...` 或 `http://192.168.x.x:8000/r/...` 当作最终队友分享链接；这些只适合本机或局域网调试。

> **安全提醒。** 公网隧道会把整个 web/WebSocket 服务暴露到互联网，而该服务当前**没有任何身份认证、授权或速率限制**。任何拿到链接的人都能创建房间、触发 demo 解析、写入房间状态。请只在可信网络下临时启用隧道，用完即关。

`/r/{room_code}` 是直达加入地址，旧的 `/?room=ROOMCODE` 仍兼容。链接打开后会自动加载房间 demo，弹出加入窗口，输入昵称并选择“旁观者”或一个 demo player 身份后加入。页面会根据协议自动选择 WebSocket：HTTPS 页面使用 `wss://`，HTTP 页面使用 `ws://`。

房间内 replay 播放状态会同步：切换 demo 并加载解析结果、切换回合、seek、播放/暂停会广播给同房间页面，切 demo 不需要重新创建房间，原 room code 和 WebSocket 会保留。进入 sandbox 后，token 位置、箭头、文字、画笔、橡皮删除、planned utility、清道具、重置推演时间等操作会实时同步；激光笔通过 cursor relay 临时显示给同房间页面，不写入保存状态。浏览器会保存一个本地稳定 client id，刷新重连时复用原 participant，不会无限堆叠 offline 记录；同一身份在新页面加入时会替换旧连接。WebSocket 会定时 heartbeat，断线后自动重连并重新拉取 room snapshot。离线 participant 会自动清理，无人活动的临时房间会过期，过期后 `/r/{room_code}` 链接不再可加入。Room state 只保存到 `outputs/rooms/*.json`，不会写回原始 replay shard，因此不会污染 demo replay 数据。

底部 `Analysis Filters` tab 是本地视图偏好，不写入 room state，也不会通过 WebSocket 同步。当前支持按阵营、玩家、finding type、severity 过滤 Findings、Utilities、Players 和地图 overlay；地图显示模式支持高亮匹配、隐藏其他、淡化其他。

#### Replay 稳定性说明

前端加载 `replay.json` 后会构建 `replayIndex`，索引回合、marker、finding、道具和 tick 范围；按回合的 shard 会按需缓存。回合切换统一走 `switchToRound()`，tick 跳转统一走 `seekToTick()` / `seekBySeconds()`，避免 round/tick/timeline/token 状态互相覆盖。

5 秒 seek 的 tickrate 优先读取 `replay.json` 中的 `match.metrics.metadata.tick_rate`，缺失时 fallback 到 64。朝向箭头会先把 CS 世界 yaw 归一化到 0-360 度，再转换到 radar canvas 向量；由于 `game_to_radar` 已反转 y 轴，canvas 向量会对 y 分量取反。yaw 缺失时优先用当前回合内最近有效 yaw，再 fallback 到移动方向，仍不可用时不画假箭头。

已知限制：当前仍只支持 Dust2；浏览器后台节流时播放会按 tickrate 跳到最近 sampled frame，而不是逐个采样帧慢慢补播。

#### 道具效果与推演道具

道具效果参数集中在 `config/utility_effects.json`，控制闪光白光、HE 爆炸/黑烟、烟雾和燃烧弹的半径、持续时间、fade in/out。导出的 demo utility 会优先使用 demo 里的真实 `expire_tick`；缺失过期事件时才使用配置中的 duration fallback，并在 `effect.used_demo_expire_tick` / `effect.used_fallback_duration` 标记来源。

Replay demo 道具和 sandbox planned utility 会正规化为同一种 `UtilityEvent`，前端共用 `drawUtilityEvent()` 渲染。Sandbox 投掷道具只写入保存方案的 `planned_utilities`，不会写回 round shard 的原始 demo `utility_events`，恢复播放 demo 后不会污染 replay 数据。

Sandbox 暂停编辑时，连续添加 smoke / flash / HE / molotov 不会推进当前推演 tick，也不会提前播放上一颗道具的爆点或范围效果；所有 planned utility 的完整轨迹会常驻显示。点击“播放效果”后才按 planned utility 的 throw / detonate / expire tick 播放轨迹与效果动画。

Sandbox 道具菜单状态机是 `idle -> utility_menu -> select_landing -> idle`：进入 sandbox 后双击人物 token，菜单按 token 的 viewport screen 坐标浮在 token 旁边，并自动 clamp 在地图容器内；拖动 token 不会弹菜单；选择 smoke/flash/HE/molotov 后进入落点选择，点击地图生成 planned utility 并关闭菜单；Esc、取消按钮或非落点模式下点击空白地图会清理选择状态。地图浮动工具栏提供 Select、Pan、Move、Arrow、Text、Brush、Eraser、Laser、Utility、Fit/Reset/Zoom 等操作，sandbox 专属工具只在推演模式显示。Brush 会保存为 `type=brush` annotation，Eraser 按 annotation id 删除箭头/文字/画笔，Laser 只作为实时指示光标发送，不进入 sandbox 保存 payload。

烟雾弹范围和颜色由 `config/utility_effects.json` 的 `smoke` 配置控制，默认半径 170。T 方烟雾使用橙黄色系，CT 方烟雾使用蓝色系，无法判断投掷方时 fallback 到中性深灰。烟雾中心可显示剩余时间饼图：`remainingRatio = (expireTick - currentTick) / (expireTick - detonateTick)`，`remainingSec = (expireTick - currentTick) / tickrate`；可在 Settings tab 通过“烟雾剩余时间”开关关闭。

### 导出 replay 数据

```bash
conda run -n cs2demo python -m cs2demo.cli export-replay samples/demos/<你的demo>.dem
```

会生成轻量 `outputs/web/{demo_id}/replay.json` 和按回合切分的 `outputs/web/{demo_id}/rounds/*.json`。Manifest 保存 match/map/rounds/findings/utility effects/utility summary 等全局轻量索引；每个 round shard 保存该回合 `frames`、`utility_events` 和 `markers`，因此大 demo 不需要在最终 web cache 中塞一个超大的全局 JSON。

CLI 默认复用已完成 cache；需要强制重建时加 `--force`。道具轨迹默认 `--utility-trajectory-mode auto`：小 demo 优先使用 `demoparser2.parse_grenades()` 的 precise projectile 坐标；大 demo 为避免一次性 projectile 解析 OOM，会保留完整 utility event/effect/marker，但 trajectory 使用投掷/爆点插值并标记 `approximate_trajectory=true`。烟雾和燃烧弹优先使用 demo expire 事件，缺失或异常时按 `config/utility_effects.json` fallback。

### 渲染击杀点

```bash
conda run -n cs2demo python -m cs2demo.cli render-kills samples/demos/<你的demo>.dem --out outputs/kills_map.png
```

### 明确不做

不调用 LLM、不接 AstrBot、不做账号登录、不做房间密码、不做公网部署平台、不做多地图（仅 Dust2）、不做 3D、不重构 parser、不迁移 React。Sandbox / 房间数据与原始 demo replay 数据严格隔离。

### 文档

更详细的项目状态、结构与更新记录见 `docs/` 目录。
