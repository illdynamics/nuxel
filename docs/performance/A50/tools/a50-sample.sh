#!/bin/sh
# A50 bounded baseline sampler (screen-on). Runs on-device, read-only, 20s.
printf 'action screen-on\n' > /run/nuxel-buttons.cmd
sleep 2
rcpu() { awk '{print $14+$15}' /proc/$1/stat 2>/dev/null; }
tot() { head -1 /proc/stat | awk '{print $2+$3+$4+$5+$6+$7+$8}'; }
p0=$(rcpu 5352); p1=$(rcpu 5399); p2=$(rcpu 5450); p3=$(rcpu 5389); t0=$(tot)
for i in $(seq 1 20); do
  sleep 1
  n0=$(rcpu 5352); n1=$(rcpu 5399); n2=$(rcpu 5450); n3=$(rcpu 5389); tn=$(tot)
  dt=$((tn-t0))
  awk -v a=$p0 -v b=$n0 -v t=$dt 'BEGIN{printf "cpu phoc=%.1f%% ", (b-a)*100/t}'
  awk -v a=$p1 -v b=$n1 -v t=$dt 'BEGIN{printf "wlfb=%.1f%% ", (b-a)*100/t}'
  awk -v a=$p2 -v b=$n2 -v t=$dt 'BEGIN{printf "webkit=%.1f%% ", (b-a)*100/t}'
  awk -v a=$p3 -v b=$n3 -v t=$dt 'BEGIN{printf "pwahost=%.1f%% ", (b-a)*100/t}'
  grep -o 'FRAMES_OK.*' /run/nuxel-wl-fb.state 2>/dev/null
  printf 'thermal BIG=%s MID=%s LITTLE=%s G3D=%s batt=%s\n' \
    "$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)" \
    "$(cat /sys/class/thermal/thermal_zone1/temp 2>/dev/null)" \
    "$(cat /sys/class/thermal/thermal_zone2/temp 2>/dev/null)" \
    "$(cat /sys/class/thermal/thermal_zone3/temp 2>/dev/null)" \
    "$(cat /sys/class/thermal/thermal_zone6/temp 2>/dev/null)"
  p0=$n0; p1=$n1; p2=$n2; p3=$n3; t0=$tn
done
