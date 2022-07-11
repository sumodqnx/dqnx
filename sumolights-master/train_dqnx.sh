#!/usr/bin/env bash
# for quick test
# python run.py -sim single -tsc dqnx -lr 0.0001 -lre 0.00000001 -nreplay 100 -nsteps 1 -target_freq 10 -updates 1 -batch 10 -save -n_layers 3 -nogui -mode train -gmin 6

# training from start no load model
# python run.py -sim single -tsc dqnx -lr 0.0001 -lre 0.00000001 -nreplay 200000 -nsteps 2 -target_freq 32 -updates 40000 -batch 32 -scale 1.5 -save -n_layers 3 -nogui -mode train -gmin 6



python run.py -sim single -tsc dqnx -lr 0.0001 -lre 0.0000001 -nreplay 200000 -nsteps 2 -target_freq 32 -updates 160000 -batch 32 -save -scale 0.8 -load -load_replay -nogui -n_layers 3 -mode train -gmin 6

python soundnotify.py