import os
import queue
import time
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from capture.screen import capture_screen
from capture.windows_api import focus_window, list_windows
from runtime.analysis_runner import AnalysisRunner
from runtime.config import DEFAULT_CONFIG_PATH, load_config, parse_region, save_config
from cv.game_regions import update_region


TILE_NAMES = {
    "honors-east": "东", "honors-south": "南", "honors-west": "西",
    "honors-north": "北", "honors-white": "白", "honors-green": "发",
    "honors-red": "中",
}


def display_tile(tile):
    if tile in TILE_NAMES:
        return TILE_NAMES[tile]
    if not tile or "-" not in tile:
        return tile or "-"
    suit, rank = tile.rsplit("-", 1)
    suffix = {"characters": "m", "dots": "p", "bamboo": "s"}.get(suit, "")
    return f"{rank}{suffix}" if suffix else tile


class QueHunApp(tk.Tk):
    POLL_MS = 100

    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.runner = None
        self.events = queue.Queue()
        self.window_lookup = {}
        self.preview_photo = None
        self.calibration_frame_size = None

        self.title("雀魂识别与 AI 分析")
        self.geometry("1180x820")
        self.minsize(980, 700)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._create_variables()
        self._build_ui()
        self.refresh_windows()
        self.after(self.POLL_MS, self._poll_events)

    def _create_variables(self):
        region = self.config["hand_region"]
        analysis = self.config.get("analysis", {})
        self.window_var = tk.StringVar(value=self.config.get("window_title", ""))
        self.region_var = tk.StringVar(
            value=f"{region['left']},{region['top']},{region['width']},{region['height']}"
        )
        self.region_mode_var = tk.StringVar(value=self.config.get("region_mode", "window"))
        self.tile_count_var = tk.StringVar(value=str(self.config.get("tile_count", 14)))
        self.delay_var = tk.StringVar(value=str(self.config.get("delay", 1.0)))
        self.stable_frames_var = tk.StringVar(value=str(self.config.get("stable_frames", 2)))
        self.cooldown_var = tk.StringVar(value=str(self.config.get("click_cooldown", 1.2)))
        self.debug_var = tk.BooleanVar(value=analysis.get("debug", False))
        self.auto_click_var = tk.BooleanVar(value=False)
        self.calibration_target_var = tk.StringVar(value="hand")
        self.status_var = tk.StringVar(value="Waiting")
        self.screen_state_var = tk.StringVar(value="unknown")
        self.hand_var = tk.StringVar(value="-")
        self.discard_var = tk.StringVar(value="-")
        self.confidence_var = tk.StringVar(value="0%")
        self.stable_var = tk.StringVar(value="否")
        self.yaku_var = tk.StringVar(value="-")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        settings = ttk.LabelFrame(self, text="窗口与校准", padding=10)
        settings.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text="雀魂窗口").grid(row=0, column=0, sticky="w")
        self.window_combo = ttk.Combobox(settings, state="readonly")
        self.window_combo.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(settings, text="刷新窗口", command=self.refresh_windows).grid(row=0, column=2)

        ttk.Label(settings, text="手牌区域").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(settings, textvariable=self.region_var).grid(
            row=1, column=1, sticky="ew", padx=8, pady=(8, 0)
        )
        calibration = ttk.Frame(settings)
        calibration.grid(row=1, column=2, pady=(8, 0))
        ttk.Combobox(
            calibration,
            textvariable=self.calibration_target_var,
            values=(
                "hand",
                "actions",
                "round_text",
                "dora_indicators",
                "discards_self",
                "discards_right",
                "discards_opposite",
                "discards_left",
            ),
            state="readonly",
            width=18,
        ).pack(side="left")
        ttk.Button(calibration, text="框选区域", command=self.calibrate).pack(
            side="left", padx=(6, 0)
        )

        options = ttk.Frame(settings)
        options.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self._option(options, "坐标", self.region_mode_var, 0, values=("window", "absolute"))
        self._option(options, "槽位", self.tile_count_var, 2, width=6)
        self._option(options, "间隔秒", self.delay_var, 4, width=7)
        self._option(options, "稳定帧", self.stable_frames_var, 6, width=6)
        self._option(options, "点击冷却", self.cooldown_var, 8, width=7)

        controls = ttk.LabelFrame(self, text="控制", padding=10)
        controls.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.start_button = ttk.Button(controls, text="Start", command=self.start)
        self.start_button.pack(side="left", padx=(0, 6))
        self.stop_button = ttk.Button(
            controls, text="Stop", command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=6)
        ttk.Button(controls, text="手动刷新", command=self.manual_refresh).pack(
            side="left", padx=6
        )
        ttk.Button(controls, text="保存设置", command=self.save_settings).pack(
            side="left", padx=6
        )
        ttk.Checkbutton(controls, text="Debug 截图", variable=self.debug_var).pack(
            side="left", padx=(18, 6)
        )
        ttk.Checkbutton(
            controls,
            text="启用自动出牌点击",
            variable=self.auto_click_var,
        ).pack(side="left", padx=6)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=3)
        left.rowconfigure(1, weight=2)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        preview_frame = ttk.LabelFrame(left, text="当前截图", padding=6)
        preview_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.preview = ttk.Label(preview_frame, text="等待截图", anchor="center")
        self.preview.grid(row=0, column=0, sticky="nsew")

        log_frame = ttk.LabelFrame(left, text="日志", padding=6)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=log_scroll.set)

        summary = ttk.LabelFrame(right, text="识别状态", padding=10)
        summary.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        summary.columnconfigure(1, weight=1)
        self._summary_row(summary, 0, "状态", self.status_var)
        self._summary_row(summary, 1, "页面", self.screen_state_var)
        self._summary_row(summary, 2, "手牌", self.hand_var, wrap=420)
        self._summary_row(summary, 3, "置信度", self.confidence_var)
        self._summary_row(summary, 4, "稳定", self.stable_var)
        self._summary_row(summary, 5, "推荐", self.discard_var)
        self._summary_row(summary, 6, "役种倾向", self.yaku_var, wrap=420)

        advice_frame = ttk.LabelFrame(right, text="Top 3 出牌建议", padding=8)
        advice_frame.grid(row=1, column=0, sticky="ew", pady=5)
        advice_frame.columnconfigure(0, weight=1)
        self.advice_text = tk.Text(advice_frame, height=14, state="disabled", wrap="word")
        self.advice_text.grid(row=0, column=0, sticky="ew")

        detail_frame = ttk.LabelFrame(right, text="OCR / 详细信息", padding=8)
        detail_frame.grid(row=2, column=0, sticky="nsew", pady=(5, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        self.detail_text = tk.Text(detail_frame, state="disabled", wrap="word")
        self.detail_text.grid(row=0, column=0, sticky="nsew")

        status = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w")
        status.grid(row=3, column=0, sticky="ew")

    @staticmethod
    def _option(parent, label, variable, column, values=None, width=10):
        ttk.Label(parent, text=label).grid(row=0, column=column, sticky="w")
        if values:
            widget = ttk.Combobox(
                parent, textvariable=variable, values=values, state="readonly", width=width
            )
        else:
            widget = ttk.Entry(parent, textvariable=variable, width=width)
        widget.grid(row=0, column=column + 1, sticky="w", padx=(4, 14))

    @staticmethod
    def _summary_row(parent, row, label, variable, wrap=None):
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky="nw", pady=2)
        ttk.Label(parent, textvariable=variable, wraplength=wrap).grid(
            row=row, column=1, sticky="w", pady=2
        )

    def refresh_windows(self):
        windows = [
            window for window in list_windows()
            if window["width"] >= 500 and window["height"] >= 400
        ]
        self.window_lookup = {
            f"{window['title']} ({window['width']}x{window['height']})": window
            for window in windows
        }
        values = list(self.window_lookup)
        self.window_combo["values"] = values
        configured = self.config.get("window_title", "")
        selected = next(
            (
                label for label, window in self.window_lookup.items()
                if window["title"] == configured
            ),
            None,
        )
        if not selected:
            selected = next(
                (
                    label for label, window in self.window_lookup.items()
                    if any(name.lower() in window["title"].lower() for name in (
                        "雀魂", "mahjongsoul", "mahjong soul",
                    ))
                ),
                values[0] if values else None,
            )
        if selected:
            self.window_combo.set(selected)
        else:
            self._append_log("未发现可用窗口；程序可启动并持续等待雀魂窗口。")

    def _selected_window(self):
        return self.window_lookup.get(self.window_combo.get())

    def calibrate(self):
        window = self._selected_window()
        if window is None:
            messagebox.showwarning("校准", "请先打开并选择雀魂窗口。", parent=self)
            return
        self.withdraw()
        try:
            focus_window(window["title"], exact=True)
            time.sleep(0.3)
            frame = capture_screen(region={
                "left": window["left"], "top": window["top"],
                "width": window["width"], "height": window["height"],
            })
            self.calibration_frame_size = (frame.shape[1], frame.shape[0])
        except Exception as exc:
            self.deiconify()
            messagebox.showerror("校准失败", str(exc), parent=self)
            return
        self.deiconify()
        self.lift()
        CalibrationDialog(self, frame, self._set_calibrated_region)

    def _set_calibrated_region(self, region):
        target = self.calibration_target_var.get()
        if target == "hand":
            self.region_mode_var.set("window")
            self.region_var.set(
                f"{region['left']},{region['top']},{region['width']},{region['height']}"
            )
            self._append_log(f"已校准手牌区域：{self.region_var.get()}")
            return
        frame_size = self.calibration_frame_size or (1920, 1080)
        stored = update_region(target, region, frame_size)
        self._append_log(f"已校准 {target} 区域：{stored}")

    def _read_settings(self):
        config = load_config(self.config_path)
        window = self._selected_window()
        if window:
            config["window_title"] = window["title"]
            config["window_title_exact"] = True
        config["region_mode"] = self.region_mode_var.get()
        config["hand_region"] = parse_region(self.region_var.get())
        window = self._selected_window()
        if window:
            config["hand_reference_size"] = {
                "width": window["width"],
                "height": window["height"],
            }
        config["tile_count"] = max(1, int(self.tile_count_var.get()))
        config["tile_slots"] = config["tile_count"]
        config["stable_frames"] = max(1, int(self.stable_frames_var.get()))
        config["delay"] = max(0.1, float(self.delay_var.get()))
        config["click_cooldown"] = max(0.0, float(self.cooldown_var.get()))
        config.setdefault("analysis", {})["debug"] = bool(self.debug_var.get())
        config.setdefault("click", {})["enabled"] = False
        return config

    def save_settings(self, quiet=False):
        try:
            self.config = self._read_settings()
            save_config(self.config, self.config_path)
        except (TypeError, ValueError) as exc:
            messagebox.showerror("设置错误", str(exc), parent=self)
            return False
        if not quiet:
            self._append_log(f"设置已保存到 {os.path.abspath(self.config_path)}")
        return True

    def start(self):
        if self.runner and self.runner.running:
            return
        if not self.save_settings(quiet=True):
            return
        auto_click = self.auto_click_var.get()
        if auto_click:
            confirmed = messagebox.askyesno(
                "确认自动点击",
                "自动点击只在前台雀魂窗口、对局状态、稳定 14 张手牌且高置信度时执行。"
                "请先在人机友人房完成只读测试。是否继续？",
                parent=self,
            )
            if not confirmed:
                self.auto_click_var.set(False)
                auto_click = False

        self.runner = AnalysisRunner(
            config_path=self.config_path,
            auto_click=auto_click,
            debug=self.debug_var.get(),
            on_result=lambda result: self.events.put(("result", result)),
            on_error=lambda exc: self.events.put(("error", exc)),
            on_status=lambda status: self.events.put(("status", status)),
            on_stopped=lambda: self.events.put(("stopped", None)),
        )
        self.runner.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Waiting")
        self._append_log("分析循环已启动。" + (" 自动点击已启用。" if auto_click else ""))

    def stop(self):
        if self.runner:
            self.runner.stop()
        self.status_var.set("Waiting")
        self.stop_button.configure(state="disabled")
        self._append_log("正在停止分析循环。")

    def manual_refresh(self):
        if self.runner and self.runner.running:
            self.runner.refresh()
            self._append_log("已请求立即刷新。")
        else:
            self.start()

    def _poll_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "result":
                    self._show_result(payload)
                elif kind == "error":
                    self.status_var.set("Error Recovering")
                    self._append_log(f"ERROR（将自动重试）：{payload}")
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "stopped":
                    self.status_var.set("Waiting")
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(self.POLL_MS, self._poll_events)

    def _show_result(self, result):
        frame = result.get("frame")
        if frame is not None:
            self._show_preview(frame)
        self.screen_state_var.set(
            f"{result.get('screen_state', 'unknown')} "
            f"({result.get('screen_confidence', 0.0):.0%})"
        )
        hand = result.get("hand") or []
        self.hand_var.set(" ".join(display_tile(tile) for tile in hand) or "-")
        self.confidence_var.set(f"{result.get('confidence', 0.0):.1%}")
        self.stable_var.set("是" if result.get("stable") else "否")
        self.discard_var.set(display_tile(result.get("discard")))
        advice = result.get("advice") or {}
        tendencies = advice.get("yaku_tendencies") or []
        self.yaku_var.set("；".join(tendencies) or "-")

        lines = []
        for index, choice in enumerate(advice.get("top_choices") or [], 1):
            lines.append(
                f"{index}. 打 {display_tile(choice['discard'])} | "
                f"{choice['shanten']} 向听 | 进张 {choice['ukeire']} | "
                f"危险度 {choice['danger']:.0%}"
            )
            lines.extend(f"   - {reason}" for reason in choice.get("reasons", []))
        for warning in advice.get("warnings") or []:
            lines.append(f"警告：{warning}")
        self._replace_text(self.advice_text, "\n".join(lines) or "暂无建议")

        detail = [
            f"动作：{result.get('action')}",
            f"点击保护：{result.get('click_reason', '-')}",
            f"点击坐标：{result.get('click') or '-'}",
            "可见动作：" + ", ".join(
                f"{item['action']}({item['confidence']:.0%})"
                for item in result.get("visible_actions") or []
            ),
            f"OCR：{result.get('ocr_text') or '(无文本/当前仅英文 OCR)'}",
        ]
        game_state = result.get("game_state") or {}
        detail.append(
            "宝牌指示：" + " ".join(
                display_tile(tile)
                for tile in game_state.get("dora_indicators") or []
            )
        )
        for player, tiles in (game_state.get("discards") or {}).items():
            detail.append(
                f"{player} 牌河：" + " ".join(display_tile(tile) for tile in tiles)
            )
        self._replace_text(self.detail_text, "\n".join(detail))
        if result.get("warning"):
            self._append_log(f"WARNING：{result['warning']}")
        elif result.get("action") == "clicked":
            self._append_log(
                f"已自动点击建议牌 {display_tile(result.get('discard'))}："
                f"{result.get('click')}"
            )

    def _show_preview(self, frame):
        rgb = frame[:, :, ::-1]
        image = Image.fromarray(rgb)
        image.thumbnail((680, 420), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=self.preview_photo, text="")

    @staticmethod
    def _replace_text(widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    def _append_log(self, line):
        timestamp = time.strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"[{timestamp}] {line}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _close(self):
        if self.runner:
            self.runner.stop()
        self.destroy()


def launch_app(config_path=DEFAULT_CONFIG_PATH):
    app = QueHunApp(config_path=config_path)
    app.mainloop()


class CalibrationDialog(tk.Toplevel):
    MAX_WIDTH = 1100
    MAX_HEIGHT = 700

    def __init__(self, parent, frame, on_selected):
        super().__init__(parent)
        self.on_selected = on_selected
        self.start = None
        self.rectangle = None
        self.title("框选完整手牌区域")
        self.transient(parent)
        self.grab_set()

        image = Image.fromarray(frame[:, :, ::-1])
        self.scale = min(1.0, self.MAX_WIDTH / image.width, self.MAX_HEIGHT / image.height)
        display_size = (
            max(1, int(round(image.width * self.scale))),
            max(1, int(round(image.height * self.scale))),
        )
        display = image.resize(display_size, Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(display)
        ttk.Label(self, text="拖动矩形，紧密框住自己的全部手牌槽位。", padding=8).pack(fill="x")
        self.canvas = tk.Canvas(
            self, width=display_size[0], height=display_size[1],
            cursor="crosshair", highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)

    def _press(self, event):
        self.start = (event.x, event.y)
        if self.rectangle is not None:
            self.canvas.delete(self.rectangle)
        self.rectangle = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="#00ff66", width=3
        )

    def _drag(self, event):
        if self.start is not None:
            self.canvas.coords(self.rectangle, self.start[0], self.start[1], event.x, event.y)

    def _release(self, event):
        if self.start is None:
            return
        left, right = sorted((self.start[0], event.x))
        top, bottom = sorted((self.start[1], event.y))
        if right - left < 20 or bottom - top < 20:
            return
        self.on_selected({
            "left": int(round(left / self.scale)),
            "top": int(round(top / self.scale)),
            "width": int(round((right - left) / self.scale)),
            "height": int(round((bottom - top) / self.scale)),
        })
        self.destroy()
