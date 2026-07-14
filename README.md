# PeachAlgo Coach

> 中文名：**黄桃算法教练**

本地优先的开源刷题教练：根据你的**编程水平、目标、主攻语言与每日时间**生成学习计划；再根据**做题反馈（难易、耗时、是否看题解）**动态调整后续题目，并安排间隔复习。

> 这不是 OJ，也不替代力扣判题。它解决的是：**刷什么、何时刷、刷完怎么调**。  
> **题库题号与题目信息来源于 LeetCode / 力扣**，仅保存元数据与外链，**不含题面**；已排除 Plus 会员专享题。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 功能

- 入门画像：语言 / 水平 / 目标 / 每日时长 / 周期 / 薄弱项
- 自动生成分阶段学习路线
- 今日任务（主线题 + 复习题 + 弱项补强）
- 做题反馈驱动的自适应调计划
- 标签掌握度与简单统计
- 精选题库元数据（题号、标签、链接，不含题面全文）
- 本地 SQLite，数据在你自己机器上
- Windows 托盘桌面版（可选）

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + TypeScript |
| 后端 | FastAPI + SQLModel |
| 数据库 | SQLite |
| 部署 | Docker Compose / 本地双进程 / Windows EXE |

## 别人怎么部署（推荐顺序）

### 方式 A：Docker 一键（最适合开源用户）

**需要：** [Docker Desktop](https://www.docker.com/products/docker-desktop/) 或 Docker Engine + Compose

```bash
git clone https://github.com/yellow-peach126/peachalgo-coach.git
cd peachalgo-coach
docker compose up --build
```

打开：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

停止：

```bash
docker compose down
```

学习数据保存在 Docker volume `coach-data` 中。

## 安全与隐私（请先读）

本项目是 **本地优先、单用户、无登录** 工具，不是面向公网的多租户服务。

| 场景 | 建议 |
|------|------|
| 本机 Docker / 本机开发 / Windows 桌面版 | ✅ 推荐 |
| 仅自己可访问的私有网络 | ✅ 可以 |
| 把 `8000` / `5173` 端口直接暴露到公网 | ❌ 不推荐 |

原因简述：

- API **没有账号鉴权**（`/api/export`、`/api/import`、`/api/reset` 等在本地自用是合理的）
- 一旦端口对公网开放，他人可能读取、覆盖或清空学习数据
- CORS 为方便本地前端，也按「本机使用」设计

**请只在本机或可信网络部署。** 若必须放到公网，请自行加反向代理鉴权 / VPN / 防火墙白名单，不要裸奔端口。

学习数据默认只存在：

- 开发模式：`backend/data/coach.db`
- Docker：volume `coach-data`
- Windows EXE：`%LOCALAPPDATA%\PeachAlgoCoach\`

仓库与镜像 **不包含** 你的个人刷题记录；也 **不包含** 任何第三方 API Key。

---

### 方式 B：本地开发双进程

**需要：** Python 3.11+、Node.js 18+

#### 1. 后端

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

健康检查：http://127.0.0.1:8000/api/health

#### 2. 前端（新开终端）

```bash
cd frontend
npm install
npm run dev
```

浏览器：http://127.0.0.1:5173  
前端已把 `/api` 代理到后端 `8000`。

---

### 方式 C：Windows 桌面 EXE（本机打包）

适合自己日常双击使用（不是给别人发源码的主路径）：

```bat
build-exe.bat
```

产物：

```text
backend\dist\PeachAlgoCoach\PeachAlgoCoach.exe
```

- 无黑窗 + 系统托盘（打开 / 退出）
- 数据：`%LOCALAPPDATA%\PeachAlgoCoach\`
- **分发时请打包整个 `PeachAlgoCoach` 文件夹**

> 打包需要本机 Node.js 与 `backend/.venv`。首次会自动安装 PyInstaller / pystray / Pillow。

Windows 开发期也可双击 `start-dev.bat` / `stop-dev.bat`。

---

## 使用流程

1. 打开站点 → **Onboarding / 设置**
2. 选择语言、水平、目标、每天可投入时间
3. 生成计划后，在 **今日任务** 查看推荐题
4. 点击「去 LeetCode」做题
5. 回来提交反馈（结果 / 难度 / 耗时）
6. 系统更新掌握度，并调整后续计划与复习

## 目录结构

```text
peachalgo-coach/
├── README.md
├── LICENSE                 # MIT
├── CONTRIBUTING.md
├── docker-compose.yml
├── docs/
│   ├── 产品设计文档.md
│   └── contribute-problems.md
├── backend/
│   ├── app/
│   ├── data/problems.json  # 题库元数据（可提交）
│   ├── desktop_app.py      # Windows 托盘入口
│   └── requirements.txt
├── frontend/
│   └── src/
└── scripts/
    └── build-exe.ps1
```

## 题库说明

```text
backend/data/problems.json
```

只包含题号、标题、难度、标签、预估时间、阶段、外链等，**不包含 LeetCode 题面全文**。

欢迎贡献更多题目元数据，见 [docs/contribute-problems.md](docs/contribute-problems.md)。

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ready` | 轻量就绪探针 |
| GET | `/api/health` | 健康检查 + 题量 |
| POST | `/api/onboarding` | 提交画像并生成计划 |
| GET | `/api/today` | 今日任务 |
| POST | `/api/attempts` | 提交做题反馈 |
| GET | `/api/plan` | 总计划 |
| GET | `/api/stats` | 掌握度统计 |
| GET | `/api/problems` | 题库列表 |
| GET | `/api/export` | 导出本地数据 |

## 设计文档

- [docs/产品设计文档.md](docs/产品设计文档.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## 路线图

- [x] 仓库骨架与本地可运行 MVP
- [x] 画像 → 计划 → 今日任务 → 反馈闭环
- [x] 基础掌握度与复习卡片
- [x] Docker / Windows 桌面打包
- [ ] 更完整的 150+ 精选题单
- [ ] 诊断题校准初始水平
- [ ] Java / Python 模板页
- [ ] 数据导入恢复
- [ ] 可选 AI 周报（用户自备 API Key）

## License

MIT — 见 [LICENSE](LICENSE)

---

**声明：** 本项目与 LeetCode / 力扣官方无关。题库仅使用公开可访问的元数据与题目链接，不提供题面转载或自动提交。仅建议在本机或私有网络自托管，勿将未加固的服务端口直接暴露到公网。
