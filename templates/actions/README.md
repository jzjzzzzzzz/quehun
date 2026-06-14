# Action Button Templates

The detector currently includes real-client templates for:

- `pon.png`
- `pass.png`

Additional calibrated templates can be added with these names:

- `chi.png`
- `kan.png`
- `riichi.png`
- `ron.png`
- `tsumo.png`

Templates should be cropped tightly around the whole rendered button at a
1920x1080 reference resolution. Detection scales them with the captured window.
Automatic action clicking is separately controlled by `action_policy` and is
disabled by default.
