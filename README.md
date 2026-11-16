# Lynx Explorer: unfocused input retains destroyed Activity

Reproduction for [lynx-family/lynx#11010](https://github.com/lynx-family/lynx/issues/11010).

Minimal ReactLynx page for the Android keyboard dispatcher lifetime bug.
No timers, subscriptions, requests, application state, or custom native modules.
The control page contains the same container and a text node, with no input.

## Environment verified

- Official Lynx 4.1.0 `LynxExplorer-noasan-release.apk`, unmodified and not repackaged.
- APK SHA-256: `6ae29787a2166974c29c2f23d87f3b20a137abcf9a8c17903ad19f3fb7f00cb6`.
- Android 15 / API 35 ARM64 emulators. Google Play image for the initial comparison;
  Google APIs userdebug image for heap collection (`AP31.240517.022/11948202`).
- Node 25.9.0, npm 11.12.1. Dependency versions are locked in package-lock.json.
- Explorer settings left at fresh-install defaults; no debugger or CDP session attached.

## Build and serve

Install the official APK from https://github.com/lynx-family/lynx/releases/tag/4.1.0
on an Android 11+ device/emulator. Actual measurements here used Android 15.

```sh
git clone https://github.com/orionmiz/lynx-input-activity-leak-repro.git
cd lynx-input-activity-leak-repro
npm ci
npm run build
python3 -m http.server 8765 --bind 127.0.0.1
```

Leave the server running. In another terminal:

```sh
adb devices
python3 reproduce.py --serial emulator-5554
```

Use your actual serial. The script force-stops Explorer once at the beginning,
opens the input page, waits three seconds, presses Back without focusing the input,
and waits three seconds. It repeats five times without killing the process.
Verify that the PID is unchanged. Do not use HOME instead of Back.

Expected: closed Activities are released; no dispatcher accumulation.
Actual: Activity count increases once per cycle, and destroyed Activities remain
strongly referenced by the SDK's static keyboard-dispatcher map after GC.

## Controls

```sh
python3 reproduce.py --serial emulator-5554 --page control
python3 reproduce.py --serial emulator-5554 --focus-at 350 440
```

The focus coordinates were verified at 1080x2400 / 420dpi. Adjust for your device.
That control opens the keyboard, verifies `mInputShown=true`, closes the keyboard,
and then closes the Activity. The script asserts if the keyboard did not open.

## Evidence and measurement caveats

`dumpsys meminfo` is an accumulation indicator, not by itself proof of a leak.
In the userdebug run, the unfocused case grew from 1 to 5 Activities in one PID.
The input heap contains five `LynxViewShellActivity`, five `q9.m` (KeyboardEvent),
and five `q9.m$g` (KeyboardInsetsAnimationDispatcher) objects. A separate HPROF
confirms all five Activities have `mDestroyed=true`, `mFinished=true`; all five
KeyboardEvents have `isStartedInUIThread=false` (`q9.m.d`). Five destroy calls
were also confirmed in logcat.

`input-five-static-paths.txt` records every path from the static map to those
five Activities, excluding `java.lang.ref.Reference.referent` edges. Obfuscated
names were mapped using the official APK's DEX and the 4.1.0 source:

- `q9.m.n`: KeyboardEvent.sInsetsAnimationDispatchers
- `q9.m$g`: KeyboardInsetsAnimationDispatcher
- `q9.m$g.a`: mHostView
- `q9.m.d`: isStartedInUIThread

The no-input and focused control traces contain **zero dispatchers** after five
cycles. Their immediate snapshots still contain one and two Activity objects,
respectively; these raw counts are not claimed to be zero or to prove independent
leaks. The focused snapshot includes an Android FrameTracker/MessageQueue path.

The Perfetto `reachable` flag does not mark this app-static path reachable in this
capture. Counts here include all recorded instances and use explicit static-field
edges, DEX verification, GC logs, and independent HPROF primitive fields rather
than filtering on `reachable`.

## Optional heap collection

Requires a userdebug/root-capable emulator (or a host build that permits heap
profiling). Root is needed only for diagnostics, not to reproduce the accumulation.
On the verified Google APIs emulator:

```sh
adb -s emulator-5556 root
adb -s emulator-5556 push heap.cfg /data/local/tmp/lynx-heap.cfg
# Run one scenario, then wait for Activity destruction to finish.
adb -s emulator-5556 shell 'cat /data/local/tmp/lynx-heap.cfg | perfetto --txt -c - -o /data/misc/perfetto-traces/lynx.pftrace'
adb -s emulator-5556 pull /data/misc/perfetto-traces/lynx.pftrace
adb -s emulator-5556 shell am dumpheap com.lynx.explorer /data/local/tmp/lynx.hprof
adb -s emulator-5556 pull /data/local/tmp/lynx.hprof
```

Raw heap dumps are not published. The provided extracted paths and primitive
fields contain only this minimal Explorer reproduction.
