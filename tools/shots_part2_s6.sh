#!/usr/bin/env bash
# Section 6 screenshots, 10 seconds apart. Timing runs one database service at a time.
cd "$(dirname "$0")/.."
shot() { tools/shot.sh "$@"; sleep 10; }
shot 30_6-1_compare_cases 'python compare.py > outputs/6_1_compare.txt; head -n 37 outputs/6_1_compare.txt'
shot 31_6-1_paths_csv_checks 'tail -n 16 outputs/6_1_compare.txt'
shot 32_6-2_bench_pg 'tools/services.sh neo stop; tools/services.sh pg status; python bench.py --engine pg | tee outputs/6_2_bench_pg.txt | tail -n 44'
shot 33_6-2_bench_neo 'tools/services.sh pg stop; tools/services.sh neo start; python bench.py --engine neo | tee outputs/6_2_bench_neo.txt | tail -n 43'
tools/services.sh pg start >/dev/null
shot 34_6-2_bench_summary 'tools/services.sh pg status; tools/services.sh neo status; python bench.py --summary | tee outputs/6_2_summary.txt'
shot 35_6-2_plans_pg 'python plans.py pg | tee outputs/6_2_plans_pg.txt'
shot 36_6-2_plans_neo 'python plans.py neo | tee outputs/6_2_plans_neo.txt'
shot 37_6-3_q7_improved_query "sed -n '308,343p' questions.py"
shot 38_6-3_recheck_q7 'python compare.py --only Q7 --q7 bidir | tee outputs/6_3_recheck_q7.txt'
shot 39_6-3_plan_before_after "grep -E 'Recursive Union|CTE Scan on (walk|fwd|bwd)|Planning Time|Execution Time' outputs/plans/pg_Q7_B_bound6.txt outputs/plans/pg_Q7_B_bound6_bidirectional.txt"
shot 40_6-3_bench_improved 'tools/services.sh neo stop; python bench.py --engine pg --q7 bidir --only Q7 --tag improved | tee outputs/6_3_bench_improved.txt; tools/services.sh neo start; python bench.py --summary | tee outputs/6_3_summary.txt | tail -n 26'
