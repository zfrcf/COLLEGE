#!/bin/bash
# usage: waitall.sh f1 f2 ...
while true; do
  done_all=1
  for f in "$@"; do grep -qE "OPTIMAL|FEASIBLE|INFEASIBLE|UNKNOWN|MODEL_INVALID|Error|Traceback" "$f" || done_all=0; done
  [ $done_all = 1 ] && break
  sleep 15
done
for f in "$@"; do echo "== $f"; grep -A40 -E "OPTIMAL|FEASIBLE|INFEASIBLE|UNKNOWN|Error|Traceback" "$f" | head -45; done
