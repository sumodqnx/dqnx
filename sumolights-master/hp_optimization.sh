#!/usr/bin/env bash
python hp_optimization.py -sim single -tsc maxpressure 
python hp_optimization.py -sim single -tsc websters
python hp_optimization.py -sim single -tsc uniform 
# python hp_optimization.py -sim single -tsc dqnx

