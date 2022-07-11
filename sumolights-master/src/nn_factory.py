import os

import tensorflow as tf

from src.neuralnets.dqn import DQN #tianxin: same for dqnx
from src.neuralnets.ddpgactor import DDPGActor
from src.neuralnets.ddpgcritic import DDPGCritic

def nn_factory( nntype, input_d, output_d, args, learner, load, tsc, n_hidden, sess=None):
    nn = None
    #tianxin: original DNN has only two layers and n_hidden is just for the number of nodes for each layer
    #tianxin: now it can be defined by on the parsed parameters
    n_nodes = args.n_hidden
    hidden_layers = [n_nodes]*args.n_layers

    if nntype == 'dqn':
        nn = DQN(input_d, hidden_layers,     
                  args.hidden_act, output_d,  
                  'linear', args.lr,          
                  args.lre, learner=learner)
    #tianxin added
    elif nntype == 'dqnx':
        nn = DQN(input_d, hidden_layers,     
                  args.hidden_act, output_d,  
                  'linear', args.lr,          
                  args.lre, learner=learner)
    elif nntype == 'ddpg':
        nn = {}
        nn['actor'] = DDPGActor(input_d, hidden_layers,     
                                args.hidden_act, output_d,  
                                'tanh', args.lr, args.lre,  
                                args.tau, learner=learner,  
                                name='actor'+tsc,           
                                batch_size=args.batch,
                                sess=sess)      
        if learner:
            #only need ddpg critic on learner procs
            nn['critic'] = DDPGCritic(input_d, hidden_layers,  
                                      args.hidden_act, 1,      
                                      'linear', args.lrc,      
                                      args.lre, args.tau,      
                                      learner=learner,         
                                      name='critic'+tsc,
                                      sess=sess)       
    else:
        #raise not found exceptions
        assert 0, 'Supplied traffic signal control argument type '+str(tsc)+' does not exist.'

    return nn

#tianxin
def get_in_out_d(tsctype, n_incoming_lanes, n_phases, n_outgoing_lanes=0):
    #+1 for the all red phase (i.e., terminal state, no vehicles at intersection)
    #tianxin: confused about it
    input_d = (n_incoming_lanes*2) + n_phases + 1
    # print("===================================================")
    # print(n_incoming_lanes)
    # print(n_phases)
    # print("===================================================")
    #tianxin added!! tricky parts
    input_dqnx = (n_incoming_lanes*2) + (n_outgoing_lanes*2) + n_phases + 1
    # print("len of outgoing lane: ", n_outgoing_lanes)
    # input_dqnx = (n_incoming_lanes*2)  + n_phases + 1
    # print("input_dqnx: ", input_dqnx)
    if tsctype == 'dqn':
        return input_d, n_phases
    elif tsctype == 'dqnx':
        return input_dqnx, n_phases
    elif tsctype == 'ddpg':
        return input_d, 1
    else:
        #raise not found exceptions
        assert 0, 'Supplied traffic signal control argument type '+str(tsc)+' does not exist.'

def gen_neural_networks(args, netdata, tsctype, tsc_ids, learner, load, n_hidden):
        neural_nets = {}
        #tianxin: added for dqnx
        if tsctype == 'dqnx':
            sess = None
            for tsc in tsc_ids:
                input_d, output_d = get_in_out_d(tsctype,
                                                 len(netdata['inter'][tsc]['incoming_lanes']),
                                                 len(netdata['inter'][tsc]['green_phases']),
                                                 len(netdata['inter'][tsc]['outgoing_lanes'])
                                                 )

                neural_nets[tsc] = nn_factory(tsctype, 
                                              input_d, 
                                              output_d, 
                                              args, 
                                              learner, 
                                              load, 
                                              tsc,
                                              n_hidden,
                                              sess=sess)
            #load the saved weights
            if load:                                                
                print('Trying to load '+str(tsctype)+' parameters ...')
                path_dirs = [args.save_path, args.tsc]                 
                for tsc in tsc_ids:                                    
                    path = '/'.join(path_dirs+[tsc])               
                    neural_nets[tsc].load_weights(path)             

                print('... successfully loaded '+str(tsctype)+' parameters')
        elif tsctype == 'dqn' or tsctype == 'ddpg':
            sess = None
            #if using tf, prepare necessary
            if tsctype == 'ddpg':

                #config = tf.ConfigProto(intra_op_parallelism_threads=1, 
                #                        inter_op_parallelism_threads=1, 
                #                        allow_soft_placement=True)

                tf.compat.v1.reset_default_graph()
                sess = tf.compat.v1.Session()
                #sess = tf.compat.v1.Session(config=config)

            #get desired neural net for each traffic signal controller
            for tsc in tsc_ids:
                input_d, output_d = get_in_out_d(tsctype,
                                                 len(netdata['inter'][tsc]['incoming_lanes']),
                                                 len(netdata['inter'][tsc]['green_phases']))

                neural_nets[tsc] = nn_factory(tsctype, 
                                              input_d, 
                                              output_d, 
                                              args, 
                                              learner, 
                                              load, 
                                              tsc,
                                              n_hidden,
                                              sess=sess)
 
            #if using tf, init all vars
            if tsctype == 'ddpg':
                sess.run(tf.compat.v1.global_variables_initializer())

            #load the saved weights
            if load:                                                
                print('Trying to load '+str(tsctype)+' parameters ...')
                path_dirs = [args.save_path, args.tsc]                 
                for tsc in tsc_ids:                                    
                    if tsctype == 'dqn':                               
                        path = '/'.join(path_dirs+[tsc])               
                        neural_nets[tsc].load_weights(path)            
                    elif tsctype == 'ddpg':                            
                        for n in neural_nets[tsc]:                     
                            path = '/'.join(path_dirs+[n,tsc])         
                            neural_nets[tsc][n].load_weights(path)     

                print('... successfully loaded '+str(tsctype)+' parameters')
        return neural_nets
