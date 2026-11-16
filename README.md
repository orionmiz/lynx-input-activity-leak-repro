# Android Activity leak from an unfocused input

A minimal reproduction of [lynx-family/lynx#11010](https://github.com/lynx-family/lynx/issues/11010).
Opening a page with an `<input>` and closing it without focusing the input leaves
its destroyed Activity retained by the SDK's static keyboard-dispatcher map.

## Run the reproduction

You need Node.js/npm, Python 3, adb, and an Android device or emulator. Install the
unmodified [Lynx Explorer 4.1.0 release APK](https://github.com/lynx-family/lynx/releases/download/4.1.0/LynxExplorer-noasan-release.apk).
The bug was verified on Android 15 ARM64; the affected SDK path runs on Android 11+.
Root is needed only for heap collection.

1. Clone, build, and serve the two test pages:

   ```sh
   git clone https://github.com/orionmiz/lynx-input-activity-leak-repro.git
   cd lynx-input-activity-leak-repro
   npm ci
   npm run build
   python3 -m http.server 8765 --bind 127.0.0.1
   ```

2. Leave the server running. In another terminal, enter the same repository
   directory and find your device serial:

   ```sh
   adb devices
   ```

3. Run the script, replacing `emulator-5554` with that serial:

   ```sh
   python3 reproduce.py --serial emulator-5554
   ```

The script opens the input page, waits three seconds, presses Back without
focusing the input, and waits another three seconds. It repeats five times and
prints the PID and Activity count after each cycle. Check that the PID stays the
same: the script resets Explorer only at the start of each scenario. If testing
manually, close the page with Back rather than HOME.

## Check the result

Closing the page should release its keyboard dispatcher and Activity. In the
reproduction, the Activity count grows from **1 to 5**. Heap inspection confirms
five destroyed Activities retained through five dispatchers.

Compare the two controls:

```sh
python3 reproduce.py --serial emulator-5554 --page control
python3 reproduce.py --serial emulator-5554 --focus-at 350 440
```

The first removes the input. The second focuses it, opens and closes the keyboard,
then closes the page. Coordinates `350 440` target the input at 1080×2400 / 420dpi;
adjust them for your device. If the script reports `Keyboard did not open`, check
the coordinates and rerun.

| Scenario | Dispatcher instances after five cycles |
| --- | --- |
| Input never focused | 5 |
| No input | 0 |
| Input focused before closing | 0 |

Activity counts from `dumpsys meminfo` indicate accumulation but do not establish
a leak on their own. [Heap verification](EVIDENCE.md) contains the retained paths,
field values, measurement limits, and commands for collecting your own heap.
