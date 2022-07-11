#!/usr/bin/env bash
for i in {1..4}
do
    python run.py -sim single -n 8 -tsc maxpressure -nogui -mode test -gmin 7 
    python run.py -sim single -n 8 -tsc websters -nogui -mode test -cmax 160 -cmin 40 -f 600 -satflow 0.3
    python run.py -sim single -n 8 -tsc uniform -nogui -mode test -gmin 14 
    python run.py -sim single -n 8 -tsc dqnx -load -nogui -mode test

done
python soundnotify.py