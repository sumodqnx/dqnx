#!/usr/bin/env bash

python run.py -sim single -tsc dqnx -lr 0.0001 -lre 0.0000001 -nreplay 200000 -nsteps 2 -target_freq 32 -updates 160000 -batch 32 -save -scale 0.8 -load -load_replay -nogui -n_layers 3 -mode train -gmin 6
