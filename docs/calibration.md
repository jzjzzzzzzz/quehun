# Real-client calibration

Recognition coordinates are stored relative to a QueHun window whenever possible. Calibrate from
a current client screenshot instead of copying coordinates from a different display scale.

## 1. Find and capture the window

Windows:

```powershell
.\.venv\Scripts\python.exe main.py --list-windows
.\.venv\Scripts\python.exe main.py --save-window-screenshot quehun.png --window-title QueHun
```

macOS:

```bash
.venv/bin/python tools/macos_permissions.py
.venv/bin/python main.py --list-windows
.venv/bin/python main.py --save-window-screenshot quehun.png --window-title QueHun
```

## 2. Configure the hand region

Measure `left,top,width,height` relative to the captured window, then save it:

```powershell
.\.venv\Scripts\python.exe main.py --configure-autoplay `
  --window-title QueHun `
  --region-mode window `
  --hand-region left,top,width,height `
  --tile-count 14 `
  --stable-frames 2 `
  --click-cooldown 1.2
```

The Tkinter UI can perform the same selection visually.

## 3. Verify in read-only mode

```powershell
.\.venv\Scripts\python.exe main.py --auto-play --iterations 5
```

Check tile labels, confidence, selected tile index, and proposed click coordinates. If recognition
is poor, enable debug capture and label the newest crops:

```powershell
.\.venv\Scripts\python.exe main.py --learn-debug-tiles m1,m2,m3,p1,p2,p3,s1,s2,s3,east,south,west,white,red
```

Use `skip` for empty or unusable crops.

## 4. Enable clicks only after verification

```powershell
.\.venv\Scripts\python.exe main.py --auto-play --enable-click
```

Keep action-button automation disabled until its templates and regions have been calibrated for the
same client layout.
