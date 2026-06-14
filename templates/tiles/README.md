# QueHun Tile Templates

Put calibrated tile crops in one directory per canonical label:

- `characters-1` through `characters-9`
- `dots-1` through `dots-9`
- `bamboo-1` through `bamboo-9`
- `honors-east`, `honors-south`, `honors-west`, `honors-north`
- `honors-white`, `honors-green`, `honors-red`

Recommended workflow:

1. Use the UI to calibrate the hand region.
2. Enable Debug and capture a stable frame. Tile crops are kept in
   `debug/tiles/latest` and are replaced on each frame.
3. Label the generated tile crops:

```powershell
.\.venv\Scripts\python.exe main.py --learn-debug-tiles m1,m2,m3,p1,p2,p3,s1,s2,s3,east,south,west,white,red
```

Use `skip` for an empty or unusable crop. The classifier also reads the legacy
`dataset/quehun-tiles` directory so existing calibrated images remain usable.
