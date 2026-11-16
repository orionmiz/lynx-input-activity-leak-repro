import argparse
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--serial", required=True)
parser.add_argument("--page", choices=["input", "control"], default="input")
parser.add_argument("--cycles", type=int, default=5)
parser.add_argument("--focus-at", nargs=2, type=int, metavar=("X", "Y"))
args = parser.parse_args()
adb = ["adb", "-s", args.serial]

def run(*argv):
    return subprocess.check_output(adb + list(argv), text=True)

# Reset only between scenarios; the process must survive between cycles.
run("shell", "am", "force-stop", "com.lynx.explorer")
run("reverse", "tcp:8765", "tcp:8765")
for cycle in range(1, args.cycles + 1):
    run("shell", "am", "start", "-n", "com.lynx.explorer/.LynxViewShellActivity",
        "--es", "lynx_initial_url", f"http://127.0.0.1:8765/dist/{args.page}.lynx.bundle")
    time.sleep(3)
    if args.focus_at:
        run("shell", "input", "tap", *map(str, args.focus_at))
        time.sleep(1)
        assert "mInputShown=true" in run("shell", "dumpsys", "input_method"), "Keyboard did not open"
        run("shell", "input", "keyevent", "4")
        time.sleep(1)
    run("shell", "input", "keyevent", "4")
    time.sleep(3)
    pid = run("shell", "pidof", "com.lynx.explorer").strip()
    meminfo = run("shell", "dumpsys", "meminfo", "com.lynx.explorer")
    print(f"cycle={cycle} pid={pid}", flush=True)
    for line in meminfo.splitlines():
        if "Activities:" in line or "Views:" in line:
            print(line, flush=True)
