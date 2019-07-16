
from plotting_tools import plotter_fraction_colors, snapshot_movie_maker_4plots
from DeepJetCore.training.DeepJet_callbacks import PredictCallback
from multiprocessing import Process
import numpy as np


class plot_pred_during_training(object):
    def __init__(self, 
               samplefile,
               output_file,
               use_event=0,
               x_index = 5,
               y_index = 6,
               z_index = 7,
               e_index = 0,
               cut_z=None,
               plotter=None,
               plotfunc=None,
               afternbatches=-1,
               on_epoch_end=True,
               decay_function=None
                 ):
        
        self.x_index = x_index 
        self.y_index = y_index 
        self.z_index = z_index 
        self.e_index = e_index 
        self.cut_z=cut_z
        if self.cut_z is not None:
            if 'pos' in self.cut_z:
                self.cut_z = 1.
            elif 'neg' in self.cut_z:
                self.cut_z = -1.
        
        self.decay_function=decay_function
        self.callback = PredictCallback(
            samplefile=samplefile,
            function_to_apply=self.make_plot, #needs to be function(counter,[model_input], [predict_output], [truth])
                 after_n_batches=afternbatches,
                 on_epoch_end=on_epoch_end,
                 use_event=use_event,
                 decay_function=self.decay_function)
        
        self.output_file=output_file
        if plotter is not None:
            self.plotter = plotter
        else:
            self.plotter = plotter_fraction_colors(output_file=output_file)
            self.plotter.gray_noise=False
        if plotfunc is not None:
            self.plotfunc=plotfunc
        else:
            self.plotfunc=None
        
    
    def make_plot(self,call_counter,feat,predicted,truth):
        # self.call_counter,self.td.x,predicted,self.td.y
        f = predicted[0][0] #list entry 0, 0th event
        if call_counter==0:
            f = truth[0][0] # make the first epoch be the truth plot
        feat = feat[0][0] #list entry 0, 0th event
        x = feat[:,self.x_index]
        y = feat[:,self.y_index]
        z = feat[:,self.z_index]
        e = feat[:,self.e_index]
        
        if self.cut_z is not None:
            x = x[z > self.cut_z]
            y = y[z > self.cut_z]
            e = e[z > self.cut_z]
            f = f[z > self.cut_z]
            z = z[z > self.cut_z]
            
        #send this to another fork so it does not prevent the training to continue
        def worker():
        
            outfile = self.output_file+str(call_counter)
            self.plotter.set_data(x,y,z,e,f)
            if self.plotfunc is not None:
                self.plotfunc()
            else:
                self.plotter.output_file=outfile
                self.plotter.plot3d()
                self.plotter.save_image()
    
        p = Process(target=worker)#, args=(,))
        p.start()
        
        
        

class plot_truth_pred_plus_coords_during_training(plot_pred_during_training):
    def __init__(self, 
               samplefile,
               output_file,
               use_event=0,
               x_index = 5,
               y_index = 6,
               z_index = 7,
               e_index = 0,
               pred_fraction_end = 20,
               transformed_x_index = 21,
               transformed_y_index = 22,
               transformed_z_index = 23,
               transformed_e_index = 24,
               cut_z=None,
               afternbatches=-1,
               on_epoch_end=True,
               **kwargs
                 ):
        plot_pred_during_training.__init__(self,samplefile,output_file,use_event,
                                           x_index,y_index,z_index,
                                           e_index=e_index,
                                           cut_z=cut_z,
                                           plotter=None,
                                           plotfunc=None,
                                           afternbatches=afternbatches,
                                           on_epoch_end=on_epoch_end, **kwargs)
        self.snapshot_maker = snapshot_movie_maker_4plots(output_file)
        
        self.transformed_x_index = transformed_x_index
        self.transformed_y_index = transformed_y_index
        self.transformed_z_index = transformed_z_index
        self.transformed_e_index = transformed_e_index
        
        self.pred_fraction_end=pred_fraction_end
        
        
    def end_job(self):
        self.snapshot_maker.end_job()
    
    def _make_e_zsel(self,z,e):
        if self.cut_z is not None:
            zsel = z > self.cut_z
            esel = e > 0.
            zsel = np.expand_dims(zsel,axis=1)
            esel = np.expand_dims(esel,axis=1)
            esel = np.concatenate([esel,zsel],axis=-1)
            esel = np.all(esel,axis=-1)
            return esel
        else: return e>0.

    def _make_plot(self,call_counter,feat,predicted,truth):
        self.snapshot_maker.glob_counter=call_counter
        
        pred  = predicted[0][0] #list entry 0, 0th event
        truth = truth[0][0] # make the first epoch be the truth plot
        feat  = feat[0][0] #list entry 0, 0th event
        
        e = feat[:,self.e_index]
        z = feat[:,self.z_index]
        x = feat[:,self.x_index]
        y = feat[:,self.y_index]
        
        esel = e>0
        ez_sel = self._make_e_zsel(z,e)
        
        
        tx = pred[:,self.transformed_x_index]
        ty = pred[:,self.transformed_y_index]
        tz = pred[:,self.transformed_z_index]
        te = pred[:,self.transformed_e_index]
        truth_fracs = truth[:,1:]
        pred_fracs = pred[:,:self.pred_fraction_end]
 
        self.snapshot_maker.reset()
        self.snapshot_maker.set_plot_data(0, x[ez_sel], y[ez_sel], z[ez_sel], e[ez_sel], truth_fracs[ez_sel]) #just the truth plot
        self.snapshot_maker.set_plot_data(1, x[ez_sel], y[ez_sel], z[ez_sel], e[ez_sel], pred_fracs[ez_sel]) #just the predicted plot
        
        self.snapshot_maker.set_plot_data(2, tx[esel], ty[esel], tz[esel], e[esel], truth_fracs[esel]) #just the predicted plot
        self.snapshot_maker.set_plot_data(3, tx[esel], ty[esel], te[esel], e[esel], truth_fracs[esel]) #just the predicted plot
        
        self.snapshot_maker.make_snapshot()
        
        
    def make_plot(self,call_counter,feat,predicted,truth):
        #send this directly to a fork so it does not interrupt training too much
        p = Process(target=self._make_plot, args=(call_counter,feat,predicted,truth))
        p.start()
        
        
        
        
        
        