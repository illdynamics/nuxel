#!/bin/sh
# A50 bounded baseline sampler v2: writes results to a file (immune to kmsg flood during sampling).
LOG=/tmp/a50-base.log
: > "$LOG"
printf 'action screen-on\n' > /run/nuxel-buttons.cmd
sleep 3
rcpu() { awk '{print $14+$15}' /proc/$1/stat 2>/dev/null; }
tot() { head -1 /proc/stat | awk '{print $2+$3+$4+$5+$6+$7+$8}'; }
p0=$(rcpu 5352); p1=$(rcpu 5399); p2=$(rcpu 5450); p3=$(rcpu 5389); t0=$(tot)
for i in $(seq 1 12); do
  sleep 1
  n0=$(rcpu 5352); n1=$(rcpu 5399); n2=$(rcpu 5450); n3=$(rcpu 5389); tn=$(tot)
  dt=$((tn-t0)); [ "$dt" -le 0 ] && dt=1
  cpu0=$(awk -v a=$p0 -v b=$n0 -v t=$dt 'BEGIN{printf "%.1f", (b-a)*100/t}')
  cpu1=$(awk -v a=$p1 -v b=$n1 -v t=$dt 'BEGIN{printf "%.1f", (b-a)*100/t}')
  cpu2=$(awk -v a=$p2 -v b=$n2 -v t=$dt 'BEGIN{printf "%.1f", (b-a)*100/t}')
  cpu3=$(awk -v a=$p3 -v b=$n3 -v t=$dt 'BEGIN{printf "%.1f", (b-a)*100/t}')
  fr=$(grep -o 'FRAMES_OK.*' /run/nuxel-wl-fb.state 2>/dev/null | head -1)
  echo "S$i phoc=${cpu0} wlfb=${cpu1} webkit=${cpu2} pwahost=${cpu3} BIG=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null) batt=$(cat /sys/class/thermal/thermal_zone6/temp 2>/dev/null)" >> "$LOG"
  echo "  $fr" >> "$LOG"
  p0=$n0; p1=$n1; p2=$n2; p3=$n3; t0=$tn
done
echo "DONE" >> "$LOG"
