# samples/demos

Put your own CS2 `.dem` files here.

Demo files are intentionally **not** committed to this repository:

- They are large binaries (often larger than GitHub's 100 MB per-file limit).
- They may contain match and player data.

`*.dem` and the rest of this directory are git-ignored (this README is the only
tracked file). After cloning, drop a `.dem` here and reference it by path, e.g.:

```bash
conda run -n cs2demo python -m cs2demo.cli parse samples/demos/your_demo.dem
```

Only Dust2 (`de_dust2`) demos are supported.

---

# samples/demos（中文）

把你自己的 CS2 `.dem` 文件放在这里。

demo 文件刻意**不**纳入本仓库：

- 体积大（常超过 GitHub 单文件 100 MB 限制）。
- 可能包含比赛与玩家数据。

`*.dem` 和本目录其余内容均被 git 忽略（只保留这个 README）。clone 后把 `.dem`
放进来并按路径引用即可。当前只支持 Dust2（`de_dust2`）。
