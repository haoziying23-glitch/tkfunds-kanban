# 泰康悦享系列 · 托管行理财年化业绩对比看板

部署在 **GitHub Pages** 的**动态**看板：GitHub Actions 每天定时抓取基金净值 → 重算成立以来年化 → 写回 `data.json` 并自动提交 → 页面读取该文件渲染。数据更新全程无需人工干预。

## 目录结构

```
├── index.html                      看板页面（读取 data.json 渲染）
├── data.json                       数据文件（Actions 自动更新；bank 段人工维护）
├── scripts/fetch_data.py           抓取 + 计算脚本
├── .github/workflows/update-data.yml  定时任务：北京时间 06:00 / 18:00
└── README.md
```

## 数据更新机制

1. 定时任务触发 → 运行 `scripts/fetch_data.py`
2. 向天天基金拉取 12 个份额的完整净值走势：
   `https://fund.eastmoney.com/pingzhongdata/<code>.js`
3. 计算成立以来年化：`(最新单位净值 ÷ 首发净值) ^ (365 ÷ 成立天数) − 1`
4. 结果写入 `data.json` 的 `taikang` 段，自动 commit 并 push
5. 页面打开时 `fetch('data.json')` 拿到最新数据

**`bank` 段（托管行数据）脚本不会覆盖** —— 招行/浦发/交银的数据没有公开接口，需人工维护。

## 首次部署

### 1. 创建仓库并推送

```bash
cd path/to/this/folder
git init
git add .
git commit -m "feat: 泰康悦享业绩对比看板"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

### 2. 开启 GitHub Pages

仓库 **Settings → Pages → Build and deployment**
- Source 选 **Deploy from a branch**
- Branch 选 `main`，目录选 `/ (root)` → Save

等 1～2 分钟，访问 `https://<用户名>.github.io/<仓库名>/` 即可。

> 若想直接用自定义域名，在 Pages 页面填写 Custom domain，并给你的域名加一条 CNAME 记录指向 `<用户名>.github.io`。

### 3. 开启 Actions 写入权限

仓库 **Settings → Actions → General → Workflow permissions**
- 勾选 **Read and write permissions** → Save

否则定时任务无法把更新后的 `data.json` push 回仓库。

### 4. 手动跑一次验证

**Actions → 更新基金净值数据 → Run workflow**，
跑完后仓库里 `data.json` 的 `updatedAt` 会变成当前时间，页面数字随之更新。

## 本地预览

必须用 HTTP 方式打开（`file://` 下 `fetch('data.json')` 会被浏览器拦截，页面会回退到内置快照）：

```bash
python -m http.server 8000
# 打开 http://127.0.0.1:8000/index.html
```

更新数据：

```bash
python scripts/fetch_data.py      # 只依赖 Python 标准库，无需 pip install
```

## 维护托管行数据

两种方式，任选其一：

| 方式 | 生效范围 | 操作 |
|---|---|---|
| 页面下方「⚙️ 托管行数据维护」 | 仅本机浏览器（localStorage） | 填数 → 保存 |
| 编辑仓库 `data.json` 的 `bank` 段 | 所有访客 | 改完 commit push，定时任务不会覆盖 |

`bank` 段格式示例：

```json
"bank": {
  "30d":  { "bankAnnual": 3.06, "asOf": "2026-09-21", "source": "招行APP（代码132082A）" },
  "180d": { "benchMin": 2.0, "benchMax": 2.2, "asOf": "2026-09-21", "source": "半年泓官方披露" }
}
```

- 有「成立以来年化」的产品用 `bankAnnual`
- 只有「业绩比较基准」的产品用 `benchMin` / `benchMax`

档位 id 对照：`30d`、`60d`、`90d`、`120d`、`180d`。

## 口径与风险提示

- 业绩比较基准 ≠ 实际收益，两者不可直接等同比较，页面仅在并置时作「目标 vs 实际」参考。
- 泰康一侧为「成立以来年化」，按净值重算，与官方口径可能存在四舍五入差异。
- 本看板仅为数据对照工具，不构成投资建议。
