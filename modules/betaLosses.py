

import tensorflow as tf
import keras.backend as K

#factorise a bit


#
#
#
#  all inputs/outputs of dimension B x V x F (with F being 1 in some cases)
#
#

def create_loss_dict(truth, pred):
    '''
    input features as
    B x V x F
    with F = colours
    
    truth as 
    B x P x P x T
    with T = [mask, true_posx, true_posy, ID_0, ID_1, ID_2, true_width, true_height, n_objects]
    
    all outputs in B x V x 1/F form except
    n_active: B x 1
    
    
    np.array(truthHitAssignementIdx, dtype='float32')   , # 1
            truthHitAssignedEnergies ,
            truthHitAssignedEtas     ,
            truthHitAssignedPhis 
            
    recHitEnergy,
            recHitEta   ,
            recHitRelPhi,
            recHitTheta ,
            recHitMag   ,
            recHitX     ,
            recHitY     ,
            recHitZ     ,
            recHitTime  
    
    '''
    outdict={}
    #make it all lists
    outdict['truthHitAssignementIdx']    =  truth[:,0]
    outdict['truthIsNoise']              =  tf.where(truth[:,0] < 0, 
                                                     tf.zeros_like(truth[:,0])+1, 
                                                     tf.zeros_like(truth[:,0]))
    outdict['truthHitAssignedEnergies']  =  truth[:,1]
    outdict['truthHitAssignedEtas']      =  truth[:,2]
    outdict['truthHitAssignedPhis']      =  truth[:,3]
    
    outdict['predBeta']       = pred[:,0]
    outdict['predEnergy']     = pred[:,1]
    outdict['predEta']        = pred[:,2]
    outdict['predPhi']        = pred[:,3]
    outdict['predCCoords']    = pred[:,4:]

    return outdict


def killNan(a):
    return tf.where(tf.is_nan(a), tf.zeros_like(a)+100., a)

def construct_ragged_matrices_indexing_tensors(row_splits):
    print('row_splits',row_splits)
    sub = row_splits[1:] - row_splits[:-1]
    a = sub**2
    b = tf.cumsum(a)
    b = tf.concat(([0], b), axis=0)
    ai = tf.ragged.row_splits_to_segment_ids(b)[..., tf.newaxis]
    b = tf.gather_nd(b, ai)
    c = tf.range(0, tf.reduce_sum(a)) - b
    vector_num_elements = tf.gather_nd(sub, ai)
    vector_range_within_batch_elements = c
    A = tf.cast(vector_range_within_batch_elements/vector_num_elements, tf.int64)[..., tf.newaxis]
    B = tf.math.floormod(vector_range_within_batch_elements,vector_num_elements)[..., tf.newaxis]


    C = tf.concat(([0], tf.cumsum(tf.gather_nd(sub, tf.ragged.row_splits_to_segment_ids(row_splits)[..., tf.newaxis]))), axis=0)

    '''
    A is like this:
    [0 0 0 0 0 1 1 1 1 1 2 2 2 2 2 3 3 3 3 3 4 4 4 4 4 0 0 0 0 1 1 1 1 2 2 2 2
     3 3 3 3 0 0 0 0 1 1 1 1 2 2 2 2 3 3 3 3 0 0 0 0 0 0 1 1 1 1 1 1 2 2 2 2 2
     2 3 3 3 3 3 3 4 4 4 4 4 4 5 5 5 5 5 5]
     
    B is like this:
    [0 1 2 3 4 0 1 2 3 4 0 1 2 3 4 0 1 2 3 4 0 1 2 3 4 0 1 2 3 0 1 2 3 0 1 2 3
     0 1 2 3 0 1 2 3 0 1 2 3 0 1 2 3 0 1 2 3 0 1 2 3 4 5 0 1 2 3 4 5 0 1 2 3 4
     5 0 1 2 3 4 5 0 1 2 3 4 5 0 1 2 3 4 5]
     
    C is like this:
    [ 0  5 10 15 20 25 29 33 37 41 45 49 53 57 63 69 75 81 87 93]
    
    C is used for constructing tensors with two ragged dimensions
     
    '''

    return A,B, C




def get_one_over_sigma(beta, beta_min=1e-3):
    return tf.zeros_like(beta) + 0.5 #1.*( 1. / (1. - beta + K.epsilon()) - 1.) + beta_min
    

def get_arb_loss(ccoords, row_splits, beta, is_noise, cluster_asso, beta_min=1e-3,
                 rep_cutoff=100):
    
    #### get dimensions right
    #padded row splits
    row_splits = tf.reshape(row_splits, (-1,))#should not be necessary
    batch_size_plus_1 = tf.cast(row_splits[-1], tf.int32)#int32 needed?
    row_splits = tf.slice(row_splits, [0], batch_size_plus_1[..., tf.newaxis])
     
    cluster_asso = tf.expand_dims(cluster_asso, axis=1)
    
    ####
    
    A,B,C = construct_ragged_matrices_indexing_tensors(row_splits)


    # Jan's losses
    # S is given (I am just setting it to all ones)
    d_square = tf.reduce_sum((tf.gather_nd(ccoords, A) - tf.gather_nd(ccoords, B))**2, axis=-1)

    d_square = tf.Print(d_square,[d_square],'d_square ')

    S = tf.reduce_sum((tf.gather_nd(cluster_asso, A) - tf.gather_nd(cluster_asso, B))**2, axis=-1)
    
    S    = tf.where( S < 0.1, tf.zeros_like(S)+1., tf.zeros_like(S))
    Snot = tf.where( S > 0.5, tf.zeros_like(S), tf.zeros_like(S)+1.)
    S    *= (1-tf.gather_nd(is_noise, A))* (1-tf.gather_nd(is_noise, B))
    Snot *= (1-tf.gather_nd(is_noise, A))* (1-tf.gather_nd(is_noise, B))

    #now this is S and Snot as defined in the paper draft

    N_minus_N_noise = tf.RaggedTensor.from_row_splits(values=(1-is_noise), row_splits=row_splits)
    N_minus_N_noise = tf.reduce_sum(N_minus_N_noise, axis=-1)+K.epsilon() # seems wrong? reduce sum, also axis?

    # This is given sorry it was easy to make a dummy version over here
    N_minus_N_noise = tf.Print(N_minus_N_noise,[tf.reduce_mean(N_minus_N_noise)],'mean N_minus_N_noise ')

    one_over_collected_sigma_i = tf.gather_nd(get_one_over_sigma(beta, beta_min), A)
    one_over_collected_sigma_j = tf.gather_nd(get_one_over_sigma(beta, beta_min), B)


    

    attractive_loss = (S*d_square)*(one_over_collected_sigma_i*one_over_collected_sigma_j)
    attractive_loss = tf.RaggedTensor.from_row_splits(values=attractive_loss, row_splits=C)
    attractive_loss = tf.RaggedTensor.from_row_splits(values=attractive_loss, row_splits=row_splits)
    attractive_loss = tf.reduce_sum(attractive_loss, axis=[1,2])
    # Normalize
    
    attractive_loss = attractive_loss / (N_minus_N_noise**2+K.epsilon())
    attractive_loss = killNan(attractive_loss)
    # Mean over the batch dimension
    attractive_loss = tf.reduce_mean(attractive_loss)



    rep_loss = (Snot)*(one_over_collected_sigma_i*one_over_collected_sigma_j)/(d_square + 1/rep_cutoff + K.epsilon())
    rep_loss = tf.RaggedTensor.from_row_splits(values=rep_loss, row_splits=C)
    rep_loss = tf.RaggedTensor.from_row_splits(values=rep_loss, row_splits=row_splits)
    rep_loss = tf.reduce_sum(rep_loss, axis=[1,2])
    # Normalize
    rep_loss = rep_loss / (N_minus_N_noise**2+K.epsilon())
    rep_loss = killNan(rep_loss)
    # Mean over the batch dimension
    rep_loss = tf.reduce_mean(rep_loss)



    # It's a ragged tensor with two ragged axes
    
    ## this one is NAN directly!
    
    min_beta_loss = tf.RaggedTensor.from_row_splits(values=(1.-S)*1e2 + (S*(one_over_collected_sigma_j)), row_splits=C)
    
   
    
    min_beta_loss = tf.RaggedTensor.from_row_splits(values=min_beta_loss, row_splits=row_splits)
    
    #this will be 0.5
    min_beta_loss = tf.reduce_min(min_beta_loss, axis=2)   
    
     ##THIS IS WEIRD OUTPUT: SHOULD BE 0.5 everywhere (see line 109)
    rep_loss = tf.Print(rep_loss,[min_beta_loss.values],'min_beta_loss ')
    
    min_beta_loss = tf.reduce_sum(min_beta_loss, axis=1)
    # Normalize
    min_beta_loss = min_beta_loss / (N_minus_N_noise+K.epsilon())
    
    
    # this kicks in immediately for no reason! there is not gradient?!?
    min_beta_loss = killNan(min_beta_loss)
    # Mean over the batch dimension
    
    #DEBUG: the output should be 0.5
    min_beta_loss = tf.reduce_mean(min_beta_loss)


    return attractive_loss, rep_loss, min_beta_loss


###### keras trick


def pre_training_loss(truth, pred):
    d = create_loss_dict(truth, pred)
    pos_loss = tf.reduce_mean((\
        (d['predEta'] - d['truthHitAssignedEtas'])**2 + \
        (d['predPhi'] - d['truthHitAssignedPhis'])**2 ))
    return pos_loss
    
    
    
def null_loss(truth, pred):
    return 0*tf.reduce_mean(pred)+0*tf.reduce_mean(truth)

def full_min_beta_loss(truth, pred, rowsplits):
    
    print('truth',truth)
    print('pred',pred)
    print('rowsplits',rowsplits)
    
    rowsplits = tf.cast(rowsplits, tf.int64)#just for first loss evaluation from stupid keras
    
    beta_min = 1e-3
    
    d = create_loss_dict(truth, pred)
    attractive_loss, rep_loss, min_beta_loss= get_arb_loss(d['predCCoords'], 
                                                           rowsplits, 
                                                           d['predBeta'], 
                                                           d['truthIsNoise'], 
                                                           d['truthHitAssignementIdx'],
                                                           beta_min=beta_min)
    
    onedivsigma = get_one_over_sigma(d['predBeta'],beta_min)
    noise_loss  = tf.reduce_mean((d['truthIsNoise']*d['predBeta'])**2)
    
    energy_loss = tf.reduce_mean(onedivsigma*(d['predEnergy'] - d['truthHitAssignedEnergies'])**2/(d['truthHitAssignedEnergies']+0.1))
    pos_loss = tf.reduce_mean(
        onedivsigma*(\
        (d['predEta'] - d['truthHitAssignedEtas'])**2 + \
        (d['predPhi'] - d['truthHitAssignedPhis'])**2 ))
    
    loss = attractive_loss + rep_loss + 100.* min_beta_loss + 100*noise_loss + energy_loss + pos_loss
    loss = tf.Print(loss,[loss,
                          attractive_loss,
                          rep_loss,
                          100.* min_beta_loss,
                          100*noise_loss,
                          energy_loss,
                          pos_loss,
                          tf.reduce_mean(d['predBeta'])], 'loss , attractive_loss + rep_loss + 100.* min_beta_loss + 100*noise_loss + energy_loss + pos_loss, mean beta ')
    return loss
    
    
subloss_passed_tensor=None
def min_beta_loss_rowsplits(truth, pred):
    global subloss_passed_tensor
    if subloss_passed_tensor is not None: #passed_tensor is actual truth
        return full_min_beta_loss(subloss_passed_tensor, pred, truth)
    subloss_passed_tensor = truth #=rs
    return  0.*tf.reduce_mean(pred)


def min_beta_loss_truth(truth, pred):
    global subloss_passed_tensor
    if subloss_passed_tensor is not None: #passed_tensor is rs from other function
        return full_min_beta_loss(truth, pred, subloss_passed_tensor)
    subloss_passed_tensor = truth #=rs
    return  0.*tf.reduce_mean(pred)





    