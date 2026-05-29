# RoundWeaver

> A CS2 demo replay, analysis, and collaborative tactics sandbox for team review.
> 本地 CS2 demo 回放、解析、沙盒推演与多人战术规划工具。Dust2 only · 不调用 LLM。

[English](#english) · [中文](#中文)

---

## English

### 1. What this project can do

#### 1.1 Demo replay

Play a CS2 `.dem` back in your browser as a clean 2D top-down view on Dust2:
round selection, prev/next round, ±5s seek, play/pause, timeline scrub, event
markers, finding jump, player tokens with health bars / names / yaw arrows, and
fine-grained utility trajectory & effect toggles.

![Demo replay in the browser](assets/screenshots/replay_desktop.png)

#### 1.2 Demo analysis

Deterministic, rule-based review (no LLM). Every finding carries evidence and is
listed in the bottom dock: trade failures, entry success/failure, stall rounds,
and post-plant losses, plus per-player metrics. A Chinese text report can be
generated from the CLI.

#### 1.3 Sandbox tactics board

Pause on any tick and enter the sandbox to plan plays: drag player tokens by
hand, double-click a token to pick a utility and simulate a throw, and free-draw
with the brush tool.

Pick a utility from the floating menu:

![Sandbox utility selection](assets/screenshots/sandbox_utility_menu.png)

Click a landing point to generate the planned throw with a dashed trajectory:

![Planned throw with dashed trajectory](assets/screenshots/sandbox_landing_trajectory.png)

Free-draw with the brush (plus eraser and laser pointer):

![Brush drawing on the map](assets/screenshots/sandbox_brush.png)

#### 1.4 Watch demos with friends & plan together

Create a room from the current demo/round/tick and invite up to 5 people. Everyone
watches the same replay, and sandbox edits (token moves, arrows, text, brush,
planned utilities, laser pointer) sync in real time over WebSocket. Friends just
open the link, pick a nickname and a side/identity, and join.

![Join a room](assets/screenshots/room_join_modal.png)

> Rooms work locally by default. To share with teammates outside your LAN, use a
> public HTTPS tunnel (`--tunnel cloudflared`). A public tunnel exposes the
> service to the internet **without authentication** — only enable it on a
> trusted network and tear it down when done.

### 2. Quickstart

#### 2.1 Install dependencies

```bash
conda create -n cs2demo python=3.12 -y
conda activate cs2demo
python -m pip install -r requirements.txt
```

#### 2.2 Get a demo

This repo does **not** ship demo files (they are large binaries and may contain
match/player data). Get a CS2 `.dem` yourself:

1. Download a demo archive.
2. Unpack it to get the `.dem` file.
3. Put the `.dem` into the `samples/demos/` folder.

Only Dust2 (`de_dust2`) demos are supported.

#### 2.3 Start using it

```bash
# Start the web app, then open http://127.0.0.1:8000
conda run -n cs2demo python -m cs2demo.server
```

In the page: pick your demo in the top dropdown, click **加载解析结果** (load),
and the replay starts. Pause and click **进入推演模式** to enter the sandbox, or
**创建房间** to start a room and invite friends.

CLI workflow (optional):

```bash
conda run -n cs2demo python -m cs2demo.cli parse        samples/demos/<your_demo>.dem
conda run -n cs2demo python -m cs2demo.cli analyze      samples/demos/<your_demo>.dem
conda run -n cs2demo python -m cs2demo.cli report       samples/demos/<your_demo>.dem
conda run -n cs2demo python -m cs2demo.cli export-replay samples/demos/<your_demo>.dem
```

---

## 中文

### 1. 这个项目能做什么

#### 1.1 Demo 回放

把 CS2 `.dem` 在网页里以 Dust2 的 2D 俯视图回放：round 选择、上一/下一回合、
前进/后退 5 秒、播放/暂停、时间轴拖动、事件 marker、finding 跳转、人物 token
血条/名字/朝向，以及细粒度的道具轨迹与效果开关。

![网页中回放 demo](assets/screenshots/replay_desktop.png)

#### 1.2 Demo 解析

确定性规则复盘，不调用 LLM。每条 finding 都带 evidence，列在底部面板：没补枪、
突破成功/失败、便秘回合、包后失败，以及玩家基础数据。还可通过 CLI 生成中文文字报告。

#### 1.3 沙盒推演

暂停在任意 tick 进入沙盒推演：手动挪动人物 token，双击 token 选择道具并模拟投掷，
还能用画笔自由涂鸦。

从浮动菜单选择道具：

![沙盒道具选择](assets/screenshots/sandbox_utility_menu.png)

点击落点生成带虚线轨迹的计划道具：

![选择落点后的虚线轨迹](assets/screenshots/sandbox_landing_trajectory.png)

用画笔自由涂鸦（另有橡皮擦和激光笔）：

![地图上的画笔涂鸦](assets/screenshots/sandbox_brush.png)

#### 1.4 邀请好友一起看 DEMO、一起做战术规划

基于当前 demo/round/tick 创建房间，最多邀请 5 人。大家观看同一份回放，沙盒里的
操作（挪 token、画箭头、文字、画笔、计划道具、激光笔）通过 WebSocket 实时同步。
好友只需打开链接，填昵称、选阵营/身份即可加入。

![加入房间](assets/screenshots/room_join_modal.png)

> 房间默认只在本机可用。要分享给不在同一局域网的队友，用公网 HTTPS 隧道
> （`--tunnel cloudflared`）。注意：公网隧道会把服务暴露到互联网且**没有任何身份
> 认证**，请只在可信网络下临时启用，用完即关。

### 2. Quickstart

#### 2.1 安装环境依赖

```bash
conda create -n cs2demo python=3.12 -y
conda activate cs2demo
python -m pip install -r requirements.txt
```

#### 2.2 获取 demo

本仓库**不包含** demo 文件（体积大且可能含比赛/玩家数据）。请自行获取 CS2 `.dem`：

1. 下载好 demo 压缩包。
2. 解压后得到 `.dem` 文件。
3. 把 `.dem` 放进 `samples/demos/` 文件夹。

当前只支持 Dust2（`de_dust2`）的 demo。

#### 2.3 开始使用

```bash
# 启动网页服务，然后打开 http://127.0.0.1:8000
conda run -n cs2demo python -m cs2demo.server
```

在页面里：顶部下拉框选择你的 demo，点击「加载解析结果」即可开始回放。暂停后点
「进入推演模式」进入沙盒，或点「创建房间」开房邀请好友。

命令行流程（可选）：

```bash
conda run -n cs2demo python -m cs2demo.cli parse         samples/demos/<你的demo>.dem
conda run -n cs2demo python -m cs2demo.cli analyze       samples/demos/<你的demo>.dem
conda run -n cs2demo python -m cs2demo.cli report        samples/demos/<你的demo>.dem
conda run -n cs2demo python -m cs2demo.cli export-replay samples/demos/<你的demo>.dem
```

