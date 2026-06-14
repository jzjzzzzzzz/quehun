import argparse
import sys
import time

from capture.screen import capture_screen
from capture.screen import save_screenshot
from capture.windows_api import find_window, list_windows
from cv.calibration import DEFAULT_DEBUG_DIR, DEFAULT_OUTPUT_DIR
from cv.calibration import learn_debug_tiles, parse_labels
from runtime.autoplay import AutoPlayController
from runtime.clicker import WindowsClicker
from runtime.config import DEFAULT_CONFIG_PATH, load_config, parse_region, save_config
from runtime.full_game import FullJapaneseGame
from runtime.japanese_game import JapaneseMahjongGame
from runtime.pipeline import Pipeline
from runtime.analyzer import AnalysisController


def configure_output():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def run(iterations=None, delay=0.5, use_screen=False):
    configure_output()
    pipeline = Pipeline()
    count = 0

    while iterations is None or count < iterations:
        frame = capture_screen() if use_screen else None
        result = pipeline.process(frame)

        if result:
            print(
                "Recommended discard: "
                f"{result['discard']} | score={result['score']} "
                f"| shanten={result['shanten']} | ukeire={result['ukeire']} "
                f"| win_p={result['win_probability']:.3f}"
            )

        count += 1
        time.sleep(delay)


def simulate(seed=None, max_turns=70):
    configure_output()
    game = JapaneseMahjongGame(seed=seed)
    history = game.play(max_turns=max_turns)

    for state in history:
        line = (
            f"turn={state['turn']} event={state['event']} "
            f"shanten={state['shanten']} wall={state['wall_remaining']}"
        )
        if state.get("decision"):
            decision = state["decision"]
            line += (
                f" discard={decision['discard']}"
                f" ukeire={decision['ukeire']}"
                f" win_p={decision['win_probability']:.3f}"
            )
        if state["waits"]:
            line += f" waits={','.join(state['waits'])}"
        print(line)

    final = history[-1]
    if final["won"]:
        print(f"Won by tsumo on {final['winning_tile']} at turn {final['turn']}.")
    else:
        print(f"No win. Final shanten={final['shanten']}, wall={final['wall_remaining']}.")


def full_game(seed=None, rounds=4, show_log=True):
    configure_output()
    game = FullJapaneseGame(seed=seed, rounds=rounds)
    result = game.play_game()

    if show_log:
        for line in result["log"]:
            print(line)

    print("Final scores:")
    for name, score in result["scores"].items():
        print(f"{name}: {score}")


def configure_autoplay(args):
    config = load_config(args.config)

    if args.window_title:
        config["window_title"] = args.window_title

    if args.region_mode:
        config["region_mode"] = args.region_mode

    if args.hand_region:
        config["hand_region"] = parse_region(args.hand_region)

    if args.tile_count:
        config["tile_count"] = args.tile_count

    if args.delay is not None:
        config["delay"] = args.delay

    if args.stable_frames:
        config["stable_frames"] = args.stable_frames

    if args.click_cooldown is not None:
        config["click_cooldown"] = args.click_cooldown

    if args.enable_click:
        config["click"]["enabled"] = True

    path = save_config(config, args.config)
    print(f"Saved autoplay config: {path}")
    print(
        f"window_title={config['window_title']!r}, "
        f"region_mode={config['region_mode']}, "
        f"hand_region={config['hand_region']}, tile_count={config['tile_count']}"
    )


def run_autoplay(args):
    config = load_config(args.config)
    click_enabled = bool(args.enable_click or config.get("click", {}).get("enabled", False))
    controller = AutoPlayController(
        config_path=args.config,
        dry_run=not click_enabled,
        debug_dir=args.auto_play_debug_dir,
    )
    controller.run(
        iterations=args.iterations,
        image_path=args.auto_play_image,
        startup_delay=args.startup_delay,
    )


def run_analysis(args):
    controller = AnalysisController(
        config_path=args.config,
        auto_click=args.analysis_auto_click,
    )
    controller.set_debug(args.debug)
    count = 0
    try:
        while args.iterations is None or count < args.iterations:
            result = controller.step()
            advice = result.get("advice") or {}
            print(
                f"status={result.get('status')} state={result.get('screen_state')} "
                f"confidence={result.get('confidence', 0.0):.3f} "
                f"hand={','.join(result.get('hand') or [])} "
                f"discard={advice.get('recommended_discard')} "
                f"action={result.get('action')} warning={result.get('warning')}",
                flush=True,
            )
            count += 1
            time.sleep(max(0.1, args.delay))
    except KeyboardInterrupt:
        print("Analysis stopped by Ctrl+C.")


def learn_autoplay_tiles(args):
    labels = parse_labels(args.learn_debug_tiles)
    written = learn_debug_tiles(
        labels=labels,
        debug_dir=args.auto_play_debug_dir or DEFAULT_DEBUG_DIR,
        output_dir=args.calibration_output_dir,
    )
    print(f"Saved {len(written)} calibrated tile crops:")
    for path in written:
        print(path)


def click_screen(args):
    clicker = WindowsClicker()
    clicker.click(args.click_screen[0], args.click_screen[1])
    print(f"Clicked screen at ({args.click_screen[0]}, {args.click_screen[1]})")


def print_windows():
    configure_output()
    for window in list_windows():
        print(
            f"{window['hwnd']}: {window['title']} "
            f"({window['left']},{window['top']},{window['width']},{window['height']})"
        )


def save_window_screenshot(path, title):
    window = find_window(title)
    if window is None:
        raise RuntimeError(f"Could not find window containing title: {title!r}")
    region = {
        "left": window["left"],
        "top": window["top"],
        "width": window["width"],
        "height": window["height"],
    }
    save_screenshot(path, region=region)
    print(f"Saved window screenshot: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--screen", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--full-game", action="store_true")
    parser.add_argument("--auto-play", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--analysis-auto-click", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--auto-play-image", default=None)
    parser.add_argument("--auto-play-debug-dir", default=None)
    parser.add_argument("--learn-debug-tiles", default=None)
    parser.add_argument("--calibration-output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--startup-delay", type=float, default=0.0)
    parser.add_argument("--configure-autoplay", action="store_true")
    parser.add_argument("--save-screenshot", default=None)
    parser.add_argument("--save-window-screenshot", default=None)
    parser.add_argument("--click-screen", nargs=2, type=int, default=None)
    parser.add_argument("--list-windows", action="store_true")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--hand-region", default=None, help="left,top,width,height")
    parser.add_argument("--region-mode", choices=("absolute", "window"), default=None)
    parser.add_argument("--window-title", default=None)
    parser.add_argument("--tile-count", type=int, default=None)
    parser.add_argument("--stable-frames", type=int, default=None)
    parser.add_argument("--click-cooldown", type=float, default=None)
    parser.add_argument("--enable-click", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-turns", type=int, default=70)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    no_command = not any(
        (
            args.list_windows,
            args.save_window_screenshot,
            args.save_screenshot,
            args.click_screen,
            args.configure_autoplay,
            args.learn_debug_tiles,
            args.auto_play,
            args.analyze,
            args.full_game,
            args.simulate,
            args.screen,
            args.iterations is not None,
        )
    )

    if args.gui or no_command:
        from ui.app import launch_app

        launch_app(config_path=args.config)
    elif args.list_windows:
        print_windows()
    elif args.save_window_screenshot:
        save_window_screenshot(args.save_window_screenshot, args.window_title or "")
    elif args.save_screenshot:
        save_screenshot(args.save_screenshot)
        print(f"Saved screenshot: {args.save_screenshot}")
    elif args.click_screen:
        click_screen(args)
    elif args.configure_autoplay:
        configure_autoplay(args)
    elif args.learn_debug_tiles:
        learn_autoplay_tiles(args)
    elif args.auto_play:
        run_autoplay(args)
    elif args.analyze:
        run_analysis(args)
    elif args.full_game:
        full_game(seed=args.seed, rounds=args.rounds, show_log=not args.quiet)
    elif args.simulate:
        simulate(seed=args.seed, max_turns=args.max_turns)
    else:
        run(iterations=args.iterations, delay=args.delay, use_screen=args.screen)


if __name__ == "__main__":
    main()
