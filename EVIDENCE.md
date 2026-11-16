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
