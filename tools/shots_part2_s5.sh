#!/usr/bin/env bash
# Section 5 screenshots, 10 seconds apart.
cd "$(dirname "$0")/.."
shot() { tools/shot.sh "$@"; sleep 10; }
shot 22_5-1_q4_results 'python run_part2.py q4 | tee outputs/5_q4.txt'
NOFRONT=1 KEEP=1 tools/shot.sh 23_5-1_q4_chart '(qlmanage -p outputs/q4_count_vs_depth.png >/dev/null 2>&1 &)' 3
pkill -f 'qlmanage -p outputs/q4_count_vs_depth.png'; osascript -e 'tell application "Terminal" to close (front window) saving no' >/dev/null 2>&1; sleep 10
shot 24_5-1_q4_queries "sed -n '133,172p' questions.py"
shot 25_5-2_5-3_q5_q6_results 'python run_part2.py q5 q6 | tee outputs/5_q5_q6.txt'
shot 26_5-2_q5_queries "sed -n '191,221p' questions.py"
shot 27_5-3_q6_queries "sed -n '222,253p' questions.py"
shot 28_5-4_q7_results 'python run_part2.py q7 | tee outputs/5_q7.txt'
shot 29_5-4_q7_queries "sed -n '262,295p' questions.py"
