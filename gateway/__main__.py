"""Run a simulated gateway:  python -m gateway --cycles 12 --outage 4-8"""
from __future__ import annotations

import argparse

from .buffer import Buffer
from .publisher import ListPublisher
from .readers import SimulatedReader
from .service import Gateway


def main() -> None:
    ap = argparse.ArgumentParser(description="Simulated edge gateway run (no hardware, no broker)")
    ap.add_argument("--cycles", type=int, default=12)
    ap.add_argument("--outage", default="4-8", help="cycle range with the uplink down, e.g. 4-8")
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.outage.split("-"))

    pub = ListPublisher()
    gw = Gateway("gw-sim", [SimulatedReader("sim-a", "dev-a"), SimulatedReader("sim-b", "dev-b", base=18.0, fail_on={3})], Buffer(), pub)
    for cycle in range(1, a.cycles + 1):
        pub.online = not (lo <= cycle <= hi)
        r = gw.run_cycle()
        h = gw.health()
        print(f"cycle {cycle:>2} link={'up  ' if pub.online else 'DOWN'} buffered+{r['buffered']} published={r['published']:>2} depth={h['buffer_depth']:>2}")
    print("health:", {k: v for k, v in gw.health().items() if k != "cpu_temp_c"})


if __name__ == "__main__":
    main()
