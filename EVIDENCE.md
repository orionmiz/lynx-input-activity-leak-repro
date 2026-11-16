# Heap verification

For setup and the three reproduction scenarios, see [README](README.md).

## Verified environment

- Unmodified official Explorer 4.1.0 release APK; SHA-256:
  `6ae29787a2166974c29c2f23d87f3b20a137abcf9a8c17903ad19f3fb7f00cb6`.
- Android 15 ARM64: Google Play image for the initial comparison, Google APIs
  userdebug image `AP31.240517.022/11948202` for heap collection.
- Explorer at fresh-install defaults, with no debugger or CDP session attached.
- Build tools: Node 25.9.0 and npm 11.12.1; dependencies locked in
  [package-lock.json](package-lock.json).

## Interpret the evidence

`dumpsys meminfo` is an accumulation indicator, not by itself proof of a leak.
In the userdebug run, the unfocused case grew from 1 to 5 Activities in one PID.
The [input heap counts](input-five-counts.csv) include five `LynxViewShellActivity`, five `q9.m` (KeyboardEvent),
and five `q9.m$g` (KeyboardInsetsAnimationDispatcher) objects. The [fields extracted from a separate HPROF](input-five-primitives.json)
confirm all five Activities have `mDestroyed=true`, `mFinished=true`; all five
KeyboardEvents have `isStartedInUIThread=false` (`q9.m.d`). Five destroy calls
were also confirmed in logcat.

[input-five-static-paths.txt](input-five-static-paths.txt) records a strong-reference
path from the static map to each of the five Activities, excluding
`java.lang.ref.Reference.referent` edges. Obfuscated
names were mapped using the official APK's DEX and the 4.1.0 source:

| APK name | Source name |
| --- | --- |
| `q9.m.n` | `KeyboardEvent.sInsetsAnimationDispatchers` |
| `q9.m$g` | `KeyboardInsetsAnimationDispatcher` |
| `q9.m$g.a` | `mHostView` |
| `q9.m.d` | `isStartedInUIThread` |

The [no-input](control-counts.csv) and [focused](focused-counts.csv) control traces contain **zero dispatchers** after five
cycles. Their immediate snapshots still contain one and two Activity objects,
respectively; these raw counts are not claimed to be zero or to prove independent
leaks. The focused snapshot includes an Android FrameTracker/MessageQueue path.

The Perfetto `reachable` flag does not mark this app-static path reachable in this
capture. Counts here include all recorded instances and use explicit static-field
edges, DEX verification, GC logs, and independent HPROF primitive fields rather
than filtering on `reachable`.

## Fix validation

Removing the start-state guards in `LynxView.destroy()` and `KeyboardEvent.stop()`
stops dispatcher accumulation in the same five-cycle script. See the
[patch](fix-validation/fix.patch).

| Scenario | Activities after each close: baseline → patched | Heap dispatchers: baseline → patched |
| --- | --- | --- |
| Input never focused | 1, 2, 3, 4, 5 → 1, 1, 1, 1, 1 | 5 → 0 |
| No input | 1, 1, 1, 1, 1 → 1, 1, 1, 1, 1 | 0 → 0 |
| Input focused before closing | 1, 2, 2, 2, 2 → 1, 2, 2, 2, 2 | 0 → 0 |

This comparison uses **two source-rebuilt Explorer APKs**, separate from the
official APK reproduction above. Both use Explorer 4.1.0 sources
(`b7eb5a809c0526bcfdca8c629848e01475f70ad9`) and Maven SDK 4.1.0.
For each variant, `LynxView.java` and `KeyboardEvent.java` were compiled from
source and substituted into the SDK AAR. The patched variant applies only the
two-guard change; the remaining SDK classes and resources are preserved.
All 32 packaged native libraries are byte-identical between the APKs.

Build settings: AGP 8.8.2, Gradle 8.12.1, Kotlin 2.1.10, compile SDK 35,
target SDK 32, ARM64, non-debuggable release, minification disabled, same signing
key. Both ran on Android 15 userdebug `AP31.240517.022/11948202`, using the same
pages and `reproduce.py` commands. Each scenario resets the process once, then
keeps it alive for five cycles. All six runs recorded five destroy calls and no
fatal or keyboard-cleanup exceptions; every focused cycle passed the keyboard-open
assertion.

[Extracted results and APK hashes](fix-validation) include per-cycle counts,
heap counts, static paths, and HPROF primitive fields. The
[baseline paths](fix-validation/baseline-input-paths.txt) retain all five destroyed
Activities through the dispatcher map. The
[patched paths](fix-validation/fixed-input-paths.txt) show no path from that map
to the one remaining Activity, and the heap contains no dispatcher instances.

The remaining Activity count is stable and matches the no-input control.
Its presence in a snapshot does not establish a separate leak: the reference
keeping that object present has not been identified. These results confirm
removal of this accumulating static-map path, not collection of every Activity
object. Other Android versions and multiple LynxViews sharing one host were not
tested.

## Collect your own heap

Requires a userdebug/root-capable emulator (or a host build that permits heap
profiling). Root is needed only for diagnostics, not to reproduce the accumulation.
Use the same serial as the reproduction run; `emulator-5556` below is an example.
Run one scenario, wait for Activity destruction to finish, then collect its heap
before starting the next scenario:

```sh
adb -s emulator-5556 root
adb -s emulator-5556 push heap.cfg /data/local/tmp/lynx-heap.cfg
adb -s emulator-5556 shell 'cat /data/local/tmp/lynx-heap.cfg | perfetto --txt -c - -o /data/misc/perfetto-traces/lynx.pftrace'
adb -s emulator-5556 pull /data/misc/perfetto-traces/lynx.pftrace
adb -s emulator-5556 shell am dumpheap com.lynx.explorer /data/local/tmp/lynx.hprof
adb -s emulator-5556 pull /data/local/tmp/lynx.hprof
```

Raw heap dumps are not published. The provided extracted paths and primitive
fields contain only this minimal Explorer reproduction.
