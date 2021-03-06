



from DeepJetCore.TrainData import TrainData, fileTimeOut
import numpy 

class TrainData_GravNetPaper(TrainData):
    '''
    This is the keras implementation of the data used in the gravnet paper (arXiv:1902.07987)
    '''
    def __init__(self):
        TrainData.__init__(self)

        self.treename="tree" #input root tree name
        
        self.truthclasses=[] #truth classes for classification
        
        self.weightbranchX='isA' #needs to be specified if weighter is used
        self.weightbranchY='isB' #needs to be specified if weighter is used
        
        #there is no need to resample/reweight
        self.weight=False
        self.remove=False
        #does not do anything in this configuration
        self.referenceclass='flatten'
        self.weight_binX = numpy.array([0,40000],dtype=float) 
        self.weight_binY = numpy.array([0,40000],dtype=float) 
        
        
        #self.registerBranches(['']) #list of branches to be used 
        
        self.registerBranches(self.truthclasses)
        
        
        #call this at the end
        self.reduceTruth(None)
        
    
    def readFromRootFile(self,filename,TupleMeanStd, weighter):
    
        # this function defines how to convert the root ntuple to the training format
        # options are not yet described here
        
        import ROOT
        fileTimeOut(filename,120) #give eos a minute to recover
        rfile = ROOT.TFile(filename)
        tree = rfile.Get(self.treename)
        self.nsamples=tree.GetEntries()
        
        
        # user code, example works with the example 2D images in root format generated by make_example_data
        from DeepJetCore.preprocessing import  readListArray
        
        # B x V x E,...
        feature_array = readListArray(filename,
                                      self.treename,
                                      "rechit_features",
                                      self.nsamples,
                                      list_size=2102, 
                                      n_feat_per_element=6)
        
        
        
        
        # B x V x E,f0,f1 
        truth_array = readListArray(filename,
                                       self.treename,
                                       "rechit_truth",
                                       self.nsamples,
                                      list_size=2102, 
                                      n_feat_per_element=3)
        
        
        
        
        self.x=[feature_array] 
        self.y=[truth_array] # we need the features also in the truth part for weighting
        self.w=[] # no event weights


