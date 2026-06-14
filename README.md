# QueHun

Windows 上的雀魂画面识别、麻将牌效率分析和可选安全点击工具。

## 启动

```powershell
.\.venv\Scripts\python.exe main.py
```

默认启动 Tkinter 工作台。先打开雀魂友人场或人机房，刷新窗口并用“截图框选”
校准自己的手牌区域。普通模式只截图和分析，不会点击。

命令行只读分析：

```powershell
.\.venv\Scripts\python.exe main.py --analyze
```

按 `Ctrl+C` 停止。Debug 模式：

```powershell
.\.venv\Scripts\python.exe main.py --analyze --debug
```

整窗截图最多保留 50 张于 `debug/screenshots`；最新手牌切片保存在
`debug/tiles/latest`。

## 自动点击

UI 中的“启用自动出牌点击”默认关闭。启用后仍必须同时满足：

- 页面识别为对局中
- 雀魂是前台窗口
- 连续帧手牌稳定
- 正好识别 14 张牌
- 总体置信度达到点击阈值
- 未重复处理同一手牌且冷却结束

“自动点击跳过”是独立开关，只允许匹配到高置信度 `pass` 模板时响应；
它仍要求总自动点击开关已启用。

仅在人机友人房校准和验证。动作按钮区域仍需针对当前客户端布局配置。

## 模板校准

Debug 截图后，将最新 14 个切片标注并导入：

```powershell
.\.venv\Scripts\python.exe main.py --learn-debug-tiles m1,m2,m3,p1,p2,p3,s1,s2,s3,east,south,west,white,red
```

标签写入 `templates/tiles`。空槽或坏切片使用 `skip`。

## OCR

程序使用系统 Tesseract 可执行文件和项目内 `tools/tessdata` 中的中英文语言
数据。没有 OCR 或单帧 OCR 失败时，程序使用视觉特征并继续下一帧。

## Extended Recognition

- `config/screen_regions.json` stores scalable regions for four discard rivers,
  dora, round wind, seat wind, and action buttons.
- The UI calibration selector can update any of these regions.
- Round/seat wind and action buttons use visual templates when OCR is unsuitable.
- River tiles learn perspective templates automatically after reliable 14-to-13
  hand transitions.
