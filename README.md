# QueHun

[![CI](https://github.com/jzjzzzzzzz/quehun/actions/workflows/ci.yml/badge.svg)](https://github.com/jzjzzzzzzz/quehun/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

<p align="center">
  <strong>简体中文</strong> · <a href="README.en.md">English</a>
</p>

雀魂画面识别、日麻牌效率分析和可选安全点击工具。项目同时提供无需游戏客户端的
四人自对局模拟器，以及 Windows/macOS 实机只读分析工作台。

## 功能

- 跨平台窗口枚举、截图和前台状态检测；
- 手牌分割、模板分类、OCR/视觉页面状态与可缩放区域识别；
- 河牌、宝牌指示牌、场风/自风和动作按钮识别；
- 向听数、有效进张、和牌、役种、危险度和前三候选弃牌说明；
- 紧凑牌谱、Unicode 麻将牌、宝牌轮转与手牌合法性工具；
- Tkinter 校准/分析界面；
- 默认关闭、具备多重前置条件的可选点击控制器；
- 可复现的日麻自对局模拟和完整回归测试。

> 当前实机分类器以本地模板/原型为主，不依赖 Torch。不同客户端版本、分辨率和缩放
> 比例需要重新校准手牌与动作区域。

## 环境要求

- Python 3.11 或更高版本；
- Windows 10/11 或 macOS；Linux 可运行纯牌理逻辑和测试；
- 可选的 Tesseract OCR。仓库内提供中英文语言数据，但仍需可执行文件；
- macOS 实机分析需要 Screen Recording 权限，点击还需要 Accessibility 权限。

## 安装

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

训练 `model/` 中的 Torch 模型时，改用：

```bash
python -m pip install -r requirements-training.txt
```

## 快速开始

启动图形工作台：

```bash
python main.py --gui
```

不带参数也会启动 UI。macOS 可以双击 `run_quehun_mac.command`，首次使用前建议运行：

```bash
python tools/macos_permissions.py
```

常用命令：

| 目的 | 命令 |
| --- | --- |
| 只读分析循环 | `python main.py --analyze` |
| Debug 分析 | `python main.py --analyze --debug` |
| 单桌模拟 | `python main.py --simulate --seed 1` |
| 四人完整对局 | `python main.py --full-game --rounds 4` |
| 窗口列表 | `python main.py --list-windows` |
| 保存窗口截图 | `python main.py --save-window-screenshot quehun.png --window-title QueHun` |
| 自动出牌 dry-run | `python main.py --auto-play --iterations 5` |

Debug 整窗截图最多保留 50 张于 `debug/screenshots`，最新手牌切片保存在
`debug/tiles/latest`。

## 实机校准

先打开雀魂友人场或人机房，然后用 UI 的“截图框选”紧密框住自己的全部手牌槽位。
也可以通过 CLI 保存窗口截图、测量 `left,top,width,height` 并写入配置。

完整步骤和 Windows/macOS 示例见 [`docs/calibration.md`](docs/calibration.md)。模板标签与
目录结构见 [`templates/tiles/README.md`](templates/tiles/README.md)。

## 点击保护

只读分析是默认模式。弃牌点击必须同时满足：

- 识别为对局中且目标窗口位于前台；
- 手牌连续帧稳定且牌数符合动作阶段；
- 总体和单牌置信度达到阈值；
- 坐标位于已校准区域；
- 不是重复处理的手牌；
- 点击冷却已经结束。

动作按钮还受到独立模板置信度、稳定帧和动作白名单限制。修改识别或点击逻辑时必须
保留这些前置条件，并先验证 dry-run。

## 开发

```bash
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
python -m pytest
python -m compileall -q ai capture cv model runtime state tools ui main.py
```

项目在 Python 3.11 和 3.13 上运行相同 CI。贡献流程、识别测试要求和提交约定见
[`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 文档

- [架构与模块边界](docs/architecture.md)
- [实机校准](docs/calibration.md)
- [麻将牌记法与校验 API](docs/mahjong_notation.md)
- [变更记录](CHANGELOG.md)
- [安全报告](SECURITY.md)

## 数据与许可

项目源码使用 [Apache License 2.0](LICENSE)。`dataset/` 中的麻将牌数据保留其独立的
[MIT License](dataset/LICENSE) 和来源说明；新增图片、模板或模型时必须记录来源与许可。
