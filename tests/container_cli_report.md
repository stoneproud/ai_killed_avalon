# Actual container and CLI validation

Status: **PASSED**. Model calls: 0.

Invocation: `D:/python311/python.exe tests/validate_container_cli.py --output work/container_validation/run-final-v1`.

Image `sealed-mail-challenge:local`: `b006c5587703ddb486babcc181da779f3f758ffb7f61894a617429f879833f52`.

Full default-container `play.py` completed 83 seat actions in 246.985s, exit 0: three successes, zero failures, three Evil discussion speeches, and completed assassination. The final winner was not forced.

## Observed isolation

- Exact shared `sandbox_args` policy used for the real probe and baseline seat launches.
- Only `/workspace` (this seat, writable) and `/input` (this seat request and published-only Git, read-only) are bind mounts.
- Image root and input reject writes; own workspace accepts its test marker.
- Only `lo` interface; external TCP connect returned ENETUNREACH (101).
- Effective capabilities zero; NoNewPrivs=1; inspected pids limit 128 and memory 1 GiB.
- Actual new host state path, other-player root paths, and Podman/Docker sockets absent.
- Tested provider credential environment names absent; no credential values logged.
- Container bot/challenge source hashes match host final source; 13 original vendor files verified.

## Build network recovery

Trusted Windows build host fetched official public library/python OCI using its existing configured proxy. SHA-256 and size checked for every config/layer blob; imported using podman load. Original Containerfile then used VM build-time Debian connectivity. Players retained --network=none.

Official selected Python manifest: `sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590`.

Command: `podman build --pull=never --http-proxy=false -t sealed-mail-challenge:local -f Containerfile .`; exit 0. Raw build and command logs were retained under `work/container_validation`, with hashes in the JSON report. Prior two TLS failures are identified as operator-reported because their raw logs were not supplied.

## Exact CLI commands and outcomes

- `doctor`: exit 0, 0.078s; exact argv and raw-log hash are in the JSON report.
- `init`: exit 0, 8.188s; exact argv and raw-log hash are in the JSON report.
- `deal`: exit 0, 0.453s; exact argv and raw-log hash are in the JSON report.
- `container-play`: exit 0, 246.985s; exact argv and raw-log hash are in the JSON report.

## Final file hashes

- `bot.py`: `ba537f8dc79823590b2cf48c162d260d4bf37cc4b55bf1dd5fb22082c9a82131`
- `challenge.py`: `109e593987a984c108a63b9d1077a8e81aba19a4f57a65d9f1482afda7952668`
- `play.py`: `e4f9c452669b68c3adb307500d8a012918a59dc3c99ae74d837974eda6b46c68`
- `Containerfile`: `cf93514fe400823bf61269302a1e97a961817def4849789acfa35e5f333ae44e`
- `README.md`: `105e8b6b89f1504fdb6dddb1801b7e7f382422556d8d9e7c267e59bd9bb07fa5`
- `tests/acquire_python_base.py`: `45dd314763e3ec98a2267e98d97b6a234397f911fa699363eb0ab61fb78eaa58`
- `tests/validate_container_cli.py`: `94ad0a038f8ddd049bc45afab4837de0603534a2e4f9d9bf2484aff018c0cdf5`
- `.containerignore`: `d4647dd01a709843af3e3b7bf152f039e1000d528241cb1f7369719751079093`

## Scope

- Filesystem/network/capability probe and full baseline game use real seat containers.
- This is a local single-engine isolation probe, not a proof against kernel or container-engine vulnerabilities.
- Attack-adapter full E2E runs are separately recorded; this container full game uses the default baseline.
- Assassination outcome is not forced; the test requires completed rules flow, not an Assassin miss.
- Attack E2E and worst-case leader-budget limitations remain documented in `bot_e2e_report.json`; this baseline container run does not enlarge those claims.
- The retained work directory contains newly generated private keys and host state. Publish this report and test code, not that room.
