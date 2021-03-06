#!/usr/bin/env python
# D. Jones - 9/1/15
"""BEAMS method for PS1 data"""
import numpy as np
from scipy.misc import logsumexp
from scipy.special import erf
from astropy.cosmology import Planck13 as cosmo
from scipy.stats import norm

class BEAMS:
    def __init__(self):
        self.clobber = False
        self.verbose = False

    def add_options(self, parser=None, usage=None, config=None):
        import optparse
        if parser == None:
            parser = optparse.OptionParser(usage=usage, conflict_handler="resolve")

        # The basics
        parser.add_option('-v', '--verbose', action="count", dest="verbose",default=1)
        parser.add_option('--debug', default=False, action="store_true",
                          help='debug mode: more output and debug files')
        parser.add_option('--clobber', default=False, action="store_true",
                          help='clobber output file')
        parser.add_option('--append', default=False, action="store_true",
                          help='open output file in append mode')

        if config:
            parser.add_option('--salt2alpha', default=config.get('lightcurve','salt2alpha'), type="float",
                              help='SALT2 alpha parameter from a spectroscopic sample (default=%default)')
            parser.add_option('--salt2beta', default=config.get('lightcurve','salt2beta'), type="float",
                              help='nominal SALT2 beta parameter from a spec. sample (default=%default)')

            parser.add_option('--zmin', default=config.get('lightcurve','zmin'), type="float",
                              help='redshift range')
            parser.add_option('--zmax', default=config.get('lightcurve','zmax'), type="float",
                              help='redshift range')

            # output and number of threads
            parser.add_option('--nthreads', default=config.get('mcmc','nthreads'), type="int",
                              help='Number of threads for MCMC')
            parser.add_option('--nwalkers', default=config.get('mcmc','nwalkers'), type="int",
                              help='Number of walkers for MCMC')
            parser.add_option('--nsteps', default=config.get('mcmc','nsteps'), type="int",
                              help='Number of steps for MCMC')
            parser.add_option('--ninit', default=config.get('mcmc','ninit'), type="int",
                              help="Number of steps before the samples wander away from the initial values and are 'burnt in'")
            parser.add_option('--ntemps', default=config.get('mcmc','ninit'), type="int",
                              help="Number of temperatures for the sampler")

            parser.add_option('--mcrandstep', default=config.get('mcmc','mcrandstep'), type="float",
                              help="random step size for initializing MCMC")
            parser.add_option('--minmethod', default=config.get('mcmc','minmethod'), type="string",
                              help="""minimization method for scipy.optimize.  L-BFGS-B is probably the best, but slow.  
SLSQP is faster.  Try others if using unbounded parameters""")
            parser.add_option('--miniter', default=config.get('mcmc','miniter'), type="int",
                              help="""number of minimization iterations - uses basinhopping
algorithm for miniter > 1""")
            parser.add_option('--forceminsuccess', default=config.getboolean('mcmc','forceminsuccess'), action="store_true",
                              help="""if true, minimizer must be successful or code will crash.
Default is to let the MCMC try to find a minimum if minimizer fails""")


            parser.add_option('--nbins', default=config.get('mcmc','nbins'), type="int",
                              help='Number of z bins')
            parser.add_option('--mcrandseed', default=config.get('bootstrap','mcrandseed'), type="int",
                              help='random seed from MC sample')

            # alternate functional models
            parser.add_option('--twogauss', default=config.getboolean('models','twogauss'), action="store_true",
                              help='two gaussians for pop. B')
            parser.add_option('--skewedgauss', default=config.getboolean('models','skewedgauss'), action="store_true",
                              help='skewed gaussian for pop. B')

            parser.add_option('-f','--fitresfile', default=config.get('inputdata','fitresfile'), type="string",
                              help='file with the input data')
            parser.add_option('-o','--outfile', default=config.get('inputdata','outfile'), type="string",
                              help='Output file with the derived parameters for each redshift bin')

        else:
            parser.add_option('--salt2alpha', default=0.147, type="float",
                              help='SALT2 alpha parameter from a spectroscopic sample (default=%default)')
            parser.add_option('--salt2beta', default=3.13, type="float",
                              help='nominal SALT2 beta parameter from a spec. sample (default=%default)')            
        
            # output and number of threads
            parser.add_option('--nthreads', default=20, type="int",
                              help='Number of threads for MCMC')
            parser.add_option('--nwalkers', default=150, type="int",
                              help='Number of walkers for MCMC')
            parser.add_option('--nsteps', default=4000, type="int",
                              help='Number of steps for MCMC')
            parser.add_option('--ninit', default=200, type="int",
                              help="Number of steps before the samples wander away from the initial values and are 'burnt in'")
            parser.add_option('--ntemps', default=0, type="int",
                              help="Number of temperatures for the sampler")
            parser.add_option('--mcrandstep', default=1e-4, type="float",
                              help="random step size for initializing MCMC")
            parser.add_option('--minmethod', default='L-BFGS-B', type="string",
                              help="""minimization method for scipy.optimize.  L-BFGS-B is probably the best, but slow.  
SLSQP is faster.  Try others if using unbounded parameters""")
            parser.add_option('--miniter', default=1, type="int",
                              help="""number of minimization iterations - uses basinhopping
algorithm for miniter > 1""")
            parser.add_option('--forceminsuccess', default=False, action="store_true",
                              help="""if true, minimizer must be successful or code will crash.
Default is to let the MCMC try to find a minimum if minimizer fails""")



            parser.add_option('--nbins', default=30, type="int",
                              help='Number of z bins')
            parser.add_option('--zmin', default=0.01, type="float",
                              help='min redshift')
            parser.add_option('--zmax', default=0.7, type="float",
                              help='min redshift')
            parser.add_option('--mcrandseed', default=0, type="int",
                              help='random seed from MC sample')
            
            # alternate functional models
            parser.add_option('--twogauss', default=False, action="store_true",
                              help='two gaussians for pop. B')
            parser.add_option('--skewedgauss', default=False, action="store_true",
                              help='skewed gaussian for pop. B')

            parser.add_option('-f','--fitresfile', default='BEAMS.input', type="string",
                              help='file with the input data')
            parser.add_option('-o','--outfile', default='beamsCosmo.out', type="string",
                              help='Output file with the derived parameters for each redshift bin')

            parser.add_option('--fix',default=[],
                              type='string',action='append',
                              help='fix specified variable to initial guess')
            parser.add_option('--bounds',default=[],
                              type='string',action='append',
                              help='variable, lower bound, upper bound.  Overrides MCMC parameter file.',
                              nargs=3)
            parser.add_option('--guess',default=[],
                              type='string',action='append',
                              help='parameter guess for specified variable.  Overrides MCMC parameter file',
                              nargs=2)
            parser.add_option('--prior',default=[],
                              type='string',action='append',
                              help='parameter prior for specified variable.  Overrides MCMC parameter file',
                              nargs=3)
            parser.add_option('--bins',default=[],
                              type='string',action='append',
                              help='number of bins for specified variable.  Overrides MCMC parameter file',
                              nargs=2)
            parser.add_option('--use',default=[],
                              type='string',action='append',
                              help='use specified variable.  Overrides MCMC parameter file',
                              nargs=2)

        parser.add_option('-p','--paramfile', default='', type="string",
                          help='BEAMS parameter file')
        parser.add_option('-m','--mcmcparamfile', default='mcmcparams.input', type="string",
                          help='file that describes MCMC input parameters')


        return(parser)

    def main(self,inputfile):
        from txtobj import txtobj
        import os


        inp = txtobj(inputfile)
        
        if not len(inp.PA):
            import exceptions
            raise exceptions.RuntimeError('Warning : no data in input file!!')            

        # open the output file
        if os.path.exists(self.options.outfile) and not self.options.clobber:
            print('Warning : files %s exists!!  Not clobbering'%self.options.outfile)

        # run the MCMC
        zcontrol = np.logspace(np.log10(self.options.zmin),np.log10(self.options.zmax),num=self.options.nbins)

        pardict,guess = self.mkParamDict(zcontrol)

        cov,samples = self.mcmc(inp,zcontrol,guess)

        root,ext = os.path.splitext(self.options.outfile)
        fout = open('%s.covmat'%root,'w')
        print >> fout, '%i'%len(cov)
        shape = np.shape(cov)[0]
        for i in range(shape):
            outline = ''
            for j in range(shape):
                outline += '%8.5e '%cov[j,i]
                if i != j:
                    print >> fout, '%8.5e'%cov[j,i]#outline
                else:
                    print >> fout, '%8.5e'%0 #outline
        fout.close()

        coverr = lambda samp: np.sqrt(np.sum((samp-np.mean(samp))*(samp-np.mean(samp)))/len(samp))

        outlinevars = ['popAmean','popAstd','popBmean','popBstd','popB2mean','popB2std','skewB',
                       'scaleA','shift','lstep','lstep_1','salt2alpha','salt2beta','salt2alpha_CC','salt2beta_CC',
                       'salt2beta_1','salt2alpha_1','salt2beta_poff','salt2beta_2slope']
        outlinefmt = " ".join(["%.4f"]*(1+len(outlinevars)*2))
        fout = open(self.options.outfile,'w')
        headerline = "# zCMB "
        for o in outlinevars: headerline += "%s %s_err "%(o,o)
        print >> fout, headerline[:-1]
        if self.options.mcrandseed: print >> fout, '# MC Sample used random seed: %i'%self.options.mcrandseed
        fout.close()
        if self.options.verbose:
            print("zCMB " + " ".join(outlinevars))

        for z,i in zip(zcontrol,range(len(zcontrol))):
            outvars = (z,)
            for v in outlinevars:
                if self.pardict[v]["use"]:
                    idx = self.pardict[v]["idx"]
                    if self.pardict[v]['zpoly'] or (i >= self.pardict[v]['bins'] and self.pardict[v]['bins'] and self.pardict[v]['bins'] != 1): 
                        idx = self.pardict[v]["idx"][0]
                    if hasattr(idx,"__len__"):
                        mean,err = np.mean(samples[:,idx[i]]),np.std(samples[:,idx[i]])
                    else:
                        mean,err = np.mean(samples[:,idx]),np.std(samples[:,idx])
                    outvars += (mean,err,)
                else: outvars += (-99,-99,)
            fout = open(self.options.outfile,'a')
            print >> fout, outlinefmt%outvars
            fout.close()
                
            if self.options.verbose:
                print(outlinefmt%outvars)

    def mcmc(self,inp,zcontrol,guess):
        from scipy.optimize import minimize,basinhopping
        import emcee
        if not inp.__dict__.has_key('PL'):
            inp.PL = 0

        # minimize, not maximize
        if self.pardict['popB2mean']['use']:
            lnlikefunc = lambda *args: -threegausslike(*args)
        elif self.pardict['skewB']['use']:
            lnlikefunc = lambda *args: -twogausslike_skew(*args)
        else:
            lnlikefunc = lambda *args: -twogausslike(*args)

        inp.mu,inp.muerr = salt2mu(x1=inp.x1,x1err=inp.x1ERR,c=inp.c,cerr=inp.cERR,mb=inp.mB,mberr=inp.mBERR,
                                   cov_x1_c=inp.COV_x1_c,cov_x1_x0=inp.COV_x1_x0,cov_c_x0=inp.COV_c_x0,
                                   alpha=self.options.salt2alpha,
                                   beta=self.options.salt2beta,
                                   x0=inp.x0,z=inp.zHD)
        inp.residerr = inp.muerr[:]
        inp.resid = inp.mu - cosmo.distmod(inp.zHD).value

                        
        bounds,usebounds = (),False
        for i in xrange(len(guess)): 
            key = getpar(i,self.pardict)
            if (not hasattr(self.pardict[key]['bounds'][0],"__len__") and not hasattr(self.pardict[key]['bounds'][1],"__len__") \
                    and not self.pardict[key]['bounds'][0] and not self.pardict[key]['bounds'][1]):
                bounds += ((None,None),)
            elif (not self.pardict[key]['addcosmo'] and self.pardict[key]['bins'] <= 1 and self.pardict[key]['bounds'][0] != self.pardict[key]['bounds'][1]) or \
                    (self.pardict[key]['bounds'][0][0] != self.pardict[key]['bounds'][1][0]): 
                if hasattr(self.pardict[key]['idx'],"__len__"):
                    if i in self.pardict[key]['idx']:
                        if self.pardict[key]['addcosmo'] or self.pardict[key]['bins'] > 1:
                            bounds += ((self.pardict[key]['bounds'][0][self.pardict[key]['idx'] == i][0],
                                        self.pardict[key]['bounds'][1][self.pardict[key]['idx'] == i][0]),)
                        else:
                            bounds += (self.pardict[key]['bounds'],)
                        usebounds = True
                    else:
                        bounds += ((None,None),)
                else:
                    if i == self.pardict[key]['idx']:
                        bounds += (self.pardict[key]['bounds'],)
                        usebounds = True
                    else:
                        bounds += ((None,None),)
            else:
                bounds += ((None,None),)
        if not usebounds: bounds = None

        if not self.options.ntemps:
            if self.options.miniter <= 1:
                md = minimize(lnlikefunc,guess,
                              args=(inp,zcontrol,self.pardict['scaleA']['use'],self.pardict,self.options.debug),
                              bounds=bounds,method=self.options.minmethod,options={'maxiter':10000,'maxfev':10000})
            else:
                md = basinhopping(lnlikefunc,guess,
                                  minimizer_kwargs = {'args':(inp,zcontrol,self.pardict['scaleA']['use'],
                                                              self.pardict,self.options.debug),
                                                      'method':self.options.minmethod,
                                                      'bounds':bounds},niter=self.options.miniter)

            if md.message != 'Optimization terminated successfully.' and \
                    md.message != 'requested number of basinhopping iterations completed successfully':
                print(md.message)
                if self.options.forceminsuccess:
                    raise RuntimeError('Error : Minimization Failed!!!')
                else:
                    print("""Warning : Minimization Failed!!!
Try some different initial guesses, or let the MCMC try and take care of it""")

        # add in the random steps
        if not self.options.ntemps:
            ndim, nwalkers = len(md["x"]), int(self.options.nwalkers)
            mcstep = np.array([])
            for i in range(len(md["x"])):
                mcstep = np.append(mcstep,getparval(i,self.pardict,'mcstep'))
            pos = [md["x"] + mcstep*np.random.randn(ndim) for i in range(nwalkers)]
        else:
            ndim, nwalkers = len(guess), int(self.options.nwalkers)
            mcstep = np.array([])
            for i in range(len(guess)):
                mcstep = np.append(mcstep,getparval(i,self.pardict,'mcstep'))
            pos = [np.array(guess) + mcstep*np.random.randn(ndim) for i in range(nwalkers)]

        if not self.options.ntemps:
            sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob,
                                            args=(inp,zcontrol,self.pardict,self.options.debug),
                                            threads=int(self.options.nthreads))
            pos, prob, state = sampler.run_mcmc(pos, self.options.ninit)
            sampler.reset()
            sampler.run_mcmc(pos, self.options.nsteps, thin=1)
        else:
            if self.pardict['popB2mean']['use']:
                lnlikefunc = threegausslike
            elif self.pardict['skewB']['use']:
                lnlikefunc = twogausslike_skew
            else:
                lnlikefunc = twogausslike

            sampler = emcee.PTSampler(self.options.ntemps,nwalkers, ndim, lnlikefunc,
                                      lnprior,
                                      loglkwargs={'inp':inp,'zcontrol':zcontrol,
                                                  'usescale':self.pardict['scaleA']['use'],
                                                  'pardict':self.pardict,
                                                  'debug':self.options.debug},
                                      logpkwargs={'pardict':self.pardict},
                                      threads=int(self.options.nthreads))
            p0 = np.zeros([self.options.ntemps,nwalkers,ndim])
            for g,i in zip(guess,xrange(len(guess))):
                key = getpar(i,self.pardict)
                p0[:,:,i] = np.random.uniform(low=g-2*self.pardict[key]['prior_std'],
                                              high=g+2*self.pardict[key]['prior_std'],
                                              size=(self.options.ntemps,nwalkers))

            for p, lprob, lnlike in sampler.sample(p0, iterations=self.options.ninit):
                pass
            sampler.reset()
            print('initialization steps finished!!')
            for p, lprob, lnlike in sampler.sample(p, lnprob0=lprob,
                                                    lnlike0=lnlike,
                                                    iterations=self.options.nsteps, thin=10):
                pass
            assert sampler.chain.shape == (self.options.ntemps, nwalkers, 
                                           self.options.nsteps/10, ndim)

        print("Mean acceptance fraction: {0:.3f}"
              .format(np.mean(sampler.acceptance_fraction)))
#        for a,i in zip(sampler.acor,range(len(sampler.acor))):
#            print("autocorrelation time for parameter %s: %s"%(
#                    getpar(i,self.pardict),a))

        samples = sampler.flatchain
        if self.options.ntemps: samples = samples[0,:]

        cov = covmat(samples[:,self.pardict['popAmean']['idx']])
        if not self.options.ntemps: print md.message
        return(cov,samples)

    def mkParamDict(self,zcontrol):
        """Make a dictionary to store all info about parameters"""
        from txtobj import txtobj
        pf = txtobj(self.options.mcmcparamfile)

        if self.options.twogauss:
            pf.use[pf.param == 'popB2mean'] = 1
            pf.use[pf.param == 'popB2std'] = 1
        if self.options.skewedgauss:
            pf.use[pf.param == 'skewB'] = 1
        if len(self.options.fix):
            for fixvar in self.options.fix:
                print('Fixing parameter %s!!'%fixvar)
                pf.fixed[pf.param == fixvar] = 1
        if len(self.options.use):
            for use in self.options.use:
                usevar,useval = use
                useval = int(useval)
                print('use = %i for parameter %s!!'%(useval,usevar))
                pf.use[pf.param == usevar] = useval
        if len(self.options.bounds):
            for bounds in self.options.bounds:
                boundsvar,lbound,ubound = bounds
                lbound,ubound = float(lbound),float(ubound)
                print('%.3f < %s < %.3f !!'%(lbound,boundsvar,ubound))
                pf.lbound[pf.param == boundsvar] = lbound
                pf.ubound[pf.param == boundsvar] = ubound
        if len(self.options.guess):
            for guess in self.options.guess:
                guessvar,guessval = guess
                guessvar = float(guessvar)
                print('initial guess = %.3f for parameter %s!!'%(
                        guessval,guessvar))
                pf.guess[pf.param == guessvar] = guessval
        if len(self.options.prior):
            for prior in self.options.prior:
                priorvar,priormean,priorstd = prior
                priormean,priorstd = float(priormean),float(priorstd)
                print('Prior = %.3f +/- %.3f for parameter %s!!'%(
                        priormean,priorstd,priorvar))
                pf.prior[pf.param == priorvar] = priormean
                pf.sigma[pf.param == priorvar] = sigma
        if len(self.options.bins):
            for bins in self.options.bins:
                binvar,nbins = bins
                nbins = float(nbins)
                print('%i bins for parameter %s!!'%(nbins,binvar))
                pf.bins[pf.param == binvar] = nbins


        self.pardict = {}
        idx = 0
        for par,i in zip(pf.param,xrange(len(pf.param))):
            self.pardict[par] = {'guess':pf.guess[i],'prior_mean':pf.prior[i],
                                 'prior_std':pf.sigma[i],'fixed':pf.fixed[i],
                                 'use':pf.use[i],'addcosmo':pf.addcosmo[i],
                                 'mcstep':self.options.mcrandstep,
                                 'bins':pf.bins[i],'zpoly':pf.zpoly[i],
                                 'bounds':(pf.lbound[i],pf.ubound[i])}
            if not pf.use[i]: self.pardict[par]['idx'] = -1
            else:
                self.pardict[par]['idx'] = idx
                if pf.addcosmo[i]:
                    if pf.bins[i] == 1:
                        self.pardict[par]['guess'] = pf.guess[i] + cosmo.distmod(zcontrol).value
                        self.pardict[par]['prior_mean'] = pf.prior[i] + cosmo.distmod(zcontrol).value
                        self.pardict[par]['idx'] = idx + np.arange(len(zcontrol))
                        self.pardict[par]['bounds'] = (pf.lbound[i] + cosmo.distmod(zcontrol).value,
                                                       pf.ubound[i] + cosmo.distmod(zcontrol).value)
                        if pf.use[i]: idx += len(zcontrol)
                    else:
                        zcontrolCC = np.logspace(np.log10(min(zcontrol)),np.log10(max(zcontrol)),pf.bins[i])
                        self.pardict[par]['guess'] = pf.guess[i] + cosmo.distmod(zcontrolCC).value
                        self.pardict[par]['prior_mean'] = pf.prior[i] + cosmo.distmod(zcontrolCC).value
                        self.pardict[par]['idx'] = idx + np.arange(len(zcontrolCC))
                        self.pardict[par]['bounds'] = (pf.lbound[i] + cosmo.distmod(zcontrol).value,
                                                       pf.ubound[i] + cosmo.distmod(zcontrol).value)

                        if pf.use[i]: idx += len(zcontrolCC)
                elif pf.bins[i]:
                    if pf.bins[i] == 1:
                        self.pardict[par]['guess'] = np.zeros(len(zcontrol)) + pf.guess[i]
                        self.pardict[par]['prior_mean'] = np.zeros(len(zcontrol)) + pf.prior[i]
                        self.pardict[par]['idx'] = idx + np.arange(len(zcontrol))
                        if pf.use[i]: idx += len(zcontrol)
                    else:
                        zcontrolCC = np.logspace(np.log10(min(zcontrol)),np.log10(max(zcontrol)),pf.bins[i])
                        self.pardict[par]['guess'] = np.zeros(len(zcontrolCC)) + pf.guess[i]
                        self.pardict[par]['prior_mean'] = np.zeros(len(zcontrolCC)) + pf.prior[i]
                        self.pardict[par]['idx'] = idx + np.arange(len(zcontrolCC))
                        self.pardict[par]['bounds'] = (np.array([pf.lbound[i]]*pf.bins[i]),
                                                       np.array([pf.ubound[i]]*pf.bins[i]))
                        if pf.use[i]: idx += len(zcontrolCC)
                elif pf.zpoly[i]:
                    self.pardict[par]['guess'] = np.append(pf.guess[i],np.array([0.]*int(pf.zpoly[i])))
                    self.pardict[par]['prior_mean'] = np.append(pf.prior[i],np.array([0.]*int(pf.zpoly[i])))
                    self.pardict[par]['idx'] = idx + np.arange(int(pf.zpoly[i])+1)
                    if pf.use[i]: idx += int(pf.zpoly[i])+1
                elif pf.use[i]: idx += 1

                if pf.fixed[i]:
                    self.pardict[par]['prior_std'] = 1e-5
                    self.pardict[par]['mcstep'] = 0
                    self.pardict[par]['bounds'] = (self.pardict[par]['prior_mean']-1e-5,self.pardict[par]['prior_mean']+1e-5)

        guess = ()
        for k in pf.param:
            if not pf.use[pf.param == k]: continue
            if hasattr(self.pardict[k]['guess'],"__len__"):
                for g in self.pardict[k]['guess']:
                    guess += (g,)
            else:
                guess += (self.pardict[k]['guess'],)

        return(self.pardict,guess)


def zmodel(x,zcontrol,zHD,pardict,corr=True):
    if not corr: from astropy.cosmology import Planck13 as cosmo
        
    muAmodel = np.zeros(len(zHD))
    if pardict['popAstd']['bins'] or pardict['popAstd']['zpoly']:
        sigAmodel = np.zeros(len(zHD))
    else: sigAmodel = None
    if pardict['popBmean']['bins'] or pardict['popBmean']['zpoly']:
        muBmodel = np.zeros(len(zHD))
    else: muBmodel = None
    if pardict['popBstd']['bins'] or pardict['popBstd']['zpoly']:
        sigBmodel = np.zeros(len(zHD))
    else: sigBmodel = None
    if pardict['popB2mean']['bins'] or pardict['popB2mean']['zpoly']:
        muB2model = np.zeros(len(zHD))
    else: muB2model = None
    if pardict['popB2std']['bins'] or pardict['popB2std']['zpoly']:
        sigB2model = np.zeros(len(zHD))
    else: sigB2model = None
    if pardict['skewB']['bins'] or pardict['skewB']['zpoly']:
        skewBmodel = np.zeros(len(zHD))
    else: skewBmodel = None

    # Ia redshift/distance model
    for zb,zb1,i in zip(zcontrol[:-1],zcontrol[1:],range(len(zcontrol))):
        mua,mua1 = x[pardict['popAmean']['idx'][i]],x[pardict['popAmean']['idx'][i+1]]
        cols = np.where((zHD >= zb) & (zHD < zb1))[0]
        if not corr: cosmod = cosmo.distmod(zHD[cols]).value; cosbin = cosmo.distmod(zb).value
        alpha = np.log10(zHD[cols]/zb)/np.log10(zb1/zb)
        if corr:
            muAmodel[cols] = (1-alpha)*mua + alpha*mua1
        else:
            muAmodel[cols] = mua + cosmod - cosbin

    # Ia dispersion
    if pardict['popAstd']['use'] and pardict['popAstd']['bins']:
        zcontrolIastd = np.logspace(np.log10(min(zcontrol)),np.log10(max(zcontrol)),len(pardict['popAstd']['idx']))
        for zb,zb1,i in zip(zcontrolIastd[:-1],zcontrolIastd[1:],range(len(zcontrolIastd))):
            cols = np.where((zHD >= zb) & (zHD < zb1))[0]
            if not corr: cosmod = cosmo.distmod(zHD[cols]).value; cosbin = cosmo.distmod(zb).value
            alpha = np.log10(zHD[cols]/zb)/np.log10(zb1/zb)
            if pardict['popAstd']['use'] and pardict['popAstd']['bins']:
                sigb_1,sigb1_1 = x[pardict['popAstd']['idx'][i]],x[pardict['popAstd']['idx'][i+1]]
                if corr:
                    sigAmodel[cols] = (1-alpha)*sigb_1 + alpha*sigb1_1
                else:
                    sigAmodel[cols] = sigb_1
    else:
        sigAmodel = np.zeros(len(zHD))+x[pardict['popAstd']['idx']]

    # CC redshift/distance model - need same # of bins for everything CC-related ATM
    if pardict['popBmean']['use'] and pardict['popBmean']['bins']:
        zcontrolCC = np.logspace(np.log10(min(zcontrol)),np.log10(max(zcontrol)),len(pardict['popBmean']['idx']))
        for zb,zb1,i in zip(zcontrolCC[:-1],zcontrolCC[1:],range(len(zcontrol))):
            cols = np.where((zHD >= zb) & (zHD < zb1))[0]
            if not corr: cosmod = cosmo.distmod(zHD[cols]).value; cosbin = cosmo.distmod(zb).value
            alpha = np.log10(zHD[cols]/zb)/np.log10(zb1/zb)
            if pardict['popBmean']['use'] and pardict['popBmean']['bins']:
                mub_1,mub1_1 = x[pardict['popBmean']['idx'][i]],x[pardict['popBmean']['idx'][i+1]]
                if corr:
                    muBmodel[cols] = (1-alpha)*mub_1 + alpha*mub1_1
                else:
                    muBmodel[cols] = mub_1 + cosmod - cosbin
            if pardict['popBstd']['use'] and pardict['popBstd']['bins']:
                sigb_1,sigb1_1 = x[pardict['popBstd']['idx'][i]],x[pardict['popBstd']['idx'][i+1]]
                if corr:
                    sigBmodel[cols] = (1-alpha)*sigb_1 + alpha*sigb1_1
                else:
                    sigBmodel[cols] = sigb_1
            if pardict['skewB']['use'] and pardict['skewB']['bins']:
                skewb,skewb1 = x[pardict['skewB']['idx'][i]],x[pardict['skewB']['idx'][i+1]]
                if corr:
                    skewBmodel[cols] = (1-alpha)*skewb + alpha*skewb1
                else:
                    skewBmodel[cols] = skewb

    # second gaussian - allowing for different # of bins
    if pardict['popB2mean']['use'] and pardict['popB2mean']['bins']:
        zcontrolCC = np.logspace(np.log10(min(zcontrol)),np.log10(max(zcontrol)),len(pardict['popB2mean']['idx']))
        for zb,zb1,i in zip(zcontrolCC[:-1],zcontrolCC[1:],range(len(zcontrol))):
            cols = np.where((zHD >= zb) & (zHD < zb1))[0]
            if not corr: cosmod = cosmo.distmod(zHD[cols]).value; cosbin = cosmo.distmod(zb).value
            alpha = np.log10(zHD[cols]/zb)/np.log10(zb1/zb)
            if pardict['popB2mean']['use'] and pardict['popB2mean']['bins']:
                mub_2,mub1_2 = x[pardict['popB2mean']['idx'][i]],x[pardict['popB2mean']['idx'][i+1]]
                if corr:
                    muB2model[cols] = (1-alpha)*mub_2 + alpha*mub1_2
                else:
                    muB2model[cols] = mub_2 + cosmod - cosbin
            if pardict['popB2std']['use'] and pardict['popB2std']['bins']:
                sigb2,sigb1_2 = x[pardict['popB2std']['idx'][i]],x[pardict['popB2std']['idx'][i+1]]
                if corr:
                    sigB2model[cols] = (1-alpha)*sigb2 + alpha*sigb1_2
                else:
                    sigB2model[cols] = sigb2


    if pardict['skewB']['use'] and not pardict['skewB']['bins'] and not pardict['skewB']['zpoly']:
        skewBmodel = np.zeros(len(zHD)) + x[pardict['skewB']['idx']]
    if pardict['popBmean']['use'] and not pardict['popBmean']['bins'] and not pardict['popBmean']['zpoly']:
        muBmodel = muAmodel + x[pardict['popBmean']['idx']]
    if pardict['popBstd']['use'] and not pardict['popBstd']['bins'] and not pardict['popBstd']['zpoly']:
        sigBmodel = x[pardict['popBstd']['idx']]
    if pardict['popBmean']['use'] and pardict['popBmean']['zpoly']:
        muBmodel = 1*muAmodel
        sigBmodel = 0
        for i,j in zip(pardict['popBmean']['idx'],
                       range(len(pardict['popBmean']['idx'])-1)):
            muBmodel += x[pardict['popBmean']['idx'][j]]*zHD**j/(1+pardict['popBmean']['idx'][-1]*zHD)
    if pardict['popBstd']['use'] and pardict['popBstd']['zpoly']:
        for i,j in zip(pardict['popBstd']['idx'],
                       range(len(pardict['popBstd']['idx']))):
            sigBmodel += x[pardict['popBstd']['idx'][j]]*zHD**j/(1+pardict['popBstd']['idx'][-1]*zHD)

    if pardict['popB2mean']['use'] and not pardict['popB2mean']['bins'] and not pardict['popB2mean']['zpoly']:
        muB2model = muAmodel + x[pardict['popB2mean']['idx']]
    if pardict['popB2std']['use'] and not pardict['popB2std']['bins'] and not pardict['popB2std']['zpoly']:
        sigB2model = x[pardict['popB2std']['idx']]
    if pardict['popB2mean']['use'] and pardict['popB2mean']['zpoly']:
        muB2model = 1*muAmodel
        sigB2model = 0
        for i,j in zip(pardict['popB2mean']['idx'],
                       range(len(pardict['popB2mean']['idx'])-1)):
            muB2model += x[pardict['popB2mean']['idx'][j]]*zHD**j/(1+pardict['popB2mean']['idx'][-1]*zHD)
    if pardict['popB2std']['use'] and pardict['popB2std']['zpoly']:
        for i,j in zip(pardict['popB2std']['idx'],
                       range(len(pardict['popB2std']['idx']))):
            sigB2model += x[pardict['popB2std']['idx'][j]]*zHD**j/(1+pardict['popB2std']['idx'][-1]*zHD)


    outdict = {'muAmodel':muAmodel,
               'sigAmodel':sigAmodel,
               'muBmodel':muBmodel,
               'sigBmodel':sigBmodel,
               'muB2model':muB2model,
               'sigB2model':sigB2model,
               'skewBmodel':skewBmodel}
    return(outdict)

def getdatamu(x,inp=None,pardict=None):

    if pardict['salt2alpha']['use'] and pardict['salt2alpha_1']['use']:
        muA,muAerr = salt2mu(x1=inp.x1,x1err=inp.x1ERR,c=inp.c,cerr=inp.cERR,mb=inp.mB,mberr=inp.mBERR,
                             cov_x1_c=inp.COV_x1_c,cov_x1_x0=inp.COV_x1_x0,cov_c_x0=inp.COV_c_x0,
                             alpha=x[pardict['salt2alpha']['idx']]+x[pardict['salt2alpha_1']['idx']]*inp.zHD,
                             beta=x[pardict['salt2beta']['idx']],
                             x0=inp.x0,z=inp.zHD)
    elif pardict['salt2alpha']['use'] and pardict['salt2beta_1']['use']:
        muA,muAerr = salt2mu(x1=inp.x1,x1err=inp.x1ERR,c=inp.c,cerr=inp.cERR,mb=inp.mB,mberr=inp.mBERR,
                             cov_x1_c=inp.COV_x1_c,cov_x1_x0=inp.COV_x1_x0,cov_c_x0=inp.COV_c_x0,
                             alpha=x[pardict['salt2alpha']['idx']],
                             beta=x[pardict['salt2beta']['idx']]+x[pardict['salt2beta_1']['idx']]*inp.zHD,
                             x0=inp.x0,z=inp.zHD)
    elif pardict['salt2alpha']['use'] and pardict['salt2beta_2slope']['use']:
        muA,muAerr = np.zeros(len(inp.x1)),np.zeros(len(inp.x1))
        hc = inp.c > -0.1; lc = inp.c <= -0.1
        muA[hc],muAerr[hc] = salt2mu(x1=inp.x1[hc],x1err=inp.x1ERR[hc],c=inp.c[hc],cerr=inp.cERR[hc],mb=inp.mB[hc],mberr=inp.mBERR[hc],
                             cov_x1_c=inp.COV_x1_c[hc],cov_x1_x0=inp.COV_x1_x0[hc],cov_c_x0=inp.COV_c_x0[hc],
                             alpha=x[pardict['salt2alpha']['idx']],
                             beta=x[pardict['salt2beta']['idx']],
                             x0=inp.x0[hc],z=inp.zHD[hc])
        muA[lc],muAerr[lc] = salt2mu(x1=inp.x1[lc],x1err=inp.x1ERR[lc],c=inp.c[lc],cerr=inp.cERR[lc],mb=inp.mB[lc],mberr=inp.mBERR[lc],
                             cov_x1_c=inp.COV_x1_c[lc],cov_x1_x0=inp.COV_x1_x0[lc],cov_c_x0=inp.COV_c_x0[lc],
                             alpha=x[pardict['salt2alpha']['idx']],
                             beta=x[pardict['salt2beta_2slope']['idx']],
                             x0=inp.x0[lc],z=inp.zHD[lc])
    elif pardict['salt2alpha']['use'] and pardict['salt2beta']['use']:
        muA,muAerr = salt2mu(x1=inp.x1,x1err=inp.x1ERR,c=inp.c,cerr=inp.cERR,mb=inp.mB,mberr=inp.mBERR,
                             cov_x1_c=inp.COV_x1_c,cov_x1_x0=inp.COV_x1_x0,cov_c_x0=inp.COV_c_x0,
                             alpha=x[pardict['salt2alpha']['idx']],beta=x[pardict['salt2beta']['idx']],
                             x0=inp.x0,z=inp.zHD)
    else: muA,muAerr = inp.mu[:],inp.muerr[:]


    return(muA,muAerr)

def getdatamu_CC(x,inp=None,pardict=None):

    muC,muCerr = salt2mu(x1=inp.x1,x1err=inp.x1ERR,c=inp.c,cerr=inp.cERR,mb=inp.mB,mberr=inp.mBERR,
                         cov_x1_c=inp.COV_x1_c,cov_x1_x0=inp.COV_x1_x0,cov_c_x0=inp.COV_c_x0,
                         alpha=x[pardict['salt2alpha_CC']['idx']],
                         beta=x[pardict['salt2beta_CC']['idx']],
                         x0=inp.x0,z=inp.zHD)

    return(muC,muCerr)


def getdatamu_poff(x,inp=None,pardict=None):

    muA,muAerr = np.zeros(len(inp.x1)),np.zeros(len(inp.x1))
    if pardict['salt2alpha']['use'] and pardict['salt2beta_1']['use']:
        sc = inp.SNSPEC == 1; nsc = inp.SNSPEC == 0
        muA[sc],muAerr[sc] = salt2mu(x1=inp.x1[sc],x1err=inp.x1ERR[sc],c=inp.c[sc],cerr=inp.cERR[sc],mb=inp.mB[sc],mberr=inp.mBERR[sc],
                             cov_x1_c=inp.COV_x1_c[sc],cov_x1_x0=inp.COV_x1_x0[sc],cov_c_x0=inp.COV_c_x0[sc],
                             alpha=x[pardict['salt2alpha']['idx']],
                             beta=x[pardict['salt2beta']['idx']]+x[pardict['salt2beta_1']['idx']]*inp.zHD[sc],
                             x0=inp.x0[sc],z=inp.zHD[sc])
        muA[nsc],muAerr[nsc] = salt2mu(x1=inp.x1[nsc],x1err=inp.x1ERR[nsc],c=inp.c[nsc],cerr=inp.cERR[nsc],mb=inp.mB[nsc],mberr=inp.mBERR[nsc],
                             cov_x1_c=inp.COV_x1_c[nsc],cov_x1_x0=inp.COV_x1_x0[nsc],cov_c_x0=inp.COV_c_x0[nsc],
                             alpha=x[pardict['salt2alpha']['idx']],
                             beta=x[pardict['salt2beta']['idx']]+x[pardict['salt2beta_poff']['idx']]+x[pardict['salt2beta_1']['idx']]*inp.zHD[nsc],
                             x0=inp.x0[nsc],z=inp.zHD[nsc])
    elif pardict['salt2alpha']['use'] and pardict['salt2beta_2slope']['use']:
        hc_sc = (inp.c > -0.1) & (inp.SNSPEC == 1); lc_sc = (inp.c <= -0.1) & (inp.SNSPEC == 1)
        hc_nsc = (inp.c > -0.1) & (inp.SNSPEC == 0); lc_nsc = (inp.c <= -0.1) & (inp.SNSPEC == 0)
        muA[hc_sc],muAerr[hc_sc] = salt2mu(x1=inp.x1[hc_sc],x1err=inp.x1ERR[hc_sc],c=inp.c[hc_sc],cerr=inp.cERR[hc_sc],mb=inp.mB[hc_sc],mberr=inp.mBERR[hc_sc],
                                           cov_x1_c=inp.COV_x1_c[hc_sc],cov_x1_x0=inp.COV_x1_x0[hc_sc],cov_c_x0=inp.COV_c_x0[hc_sc],
                                           alpha=x[pardict['salt2alpha']['idx']],
                                           beta=x[pardict['salt2beta']['idx']],
                                           x0=inp.x0[hc_sc],z=inp.zHD[hc_sc])
        muA[lc_sc],muAerr[lc_sc] = salt2mu(x1=inp.x1[lc_sc],x1err=inp.x1ERR[lc_sc],c=inp.c[lc_sc],cerr=inp.cERR[lc_sc],mb=inp.mB[lc_sc],mberr=inp.mBERR[lc_sc],
                                           cov_x1_c=inp.COV_x1_c[lc_sc],cov_x1_x0=inp.COV_x1_x0[lc_sc],cov_c_x0=inp.COV_c_x0[lc_sc],
                                           alpha=x[pardict['salt2alpha']['idx']],
                                           beta=x[pardict['salt2beta_2slope']['idx']],
                                           x0=inp.x0[lc_sc],z=inp.zHD[lc_sc])
        muA[hc_nsc],muAerr[hc_nsc] = salt2mu(x1=inp.x1[hc_nsc],x1err=inp.x1ERR[hc_nsc],c=inp.c[hc_nsc],cerr=inp.cERR[hc_nsc],mb=inp.mB[hc_nsc],mberr=inp.mBERR[hc_nsc],
                                             cov_x1_c=inp.COV_x1_c[hc_nsc],cov_x1_x0=inp.COV_x1_x0[hc_nsc],cov_c_x0=inp.COV_c_x0[hc_nsc],
                                             alpha=x[pardict['salt2alpha']['idx']],
                                             beta=x[pardict['salt2beta']['idx']]+x[pardict['salt2beta_poff']['idx']],
                                             x0=inp.x0[hc_nsc],z=inp.zHD[hc_nsc])
        muA[lc_nsc],muAerr[lc_nsc] = salt2mu(x1=inp.x1[lc_nsc],x1err=inp.x1ERR[lc_nsc],c=inp.c[lc_nsc],cerr=inp.cERR[lc_nsc],mb=inp.mB[lc_nsc],mberr=inp.mBERR[lc_nsc],
                                             cov_x1_c=inp.COV_x1_c[lc_nsc],cov_x1_x0=inp.COV_x1_x0[lc_nsc],cov_c_x0=inp.COV_c_x0[lc_nsc],
                                             alpha=x[pardict['salt2alpha']['idx']],
                                             beta=x[pardict['salt2beta_2slope']['idx']]+x[pardict['salt2beta_poff']['idx']],
                                             x0=inp.x0[lc_nsc],z=inp.zHD[lc_nsc])
    elif pardict['salt2alpha']['use'] and pardict['salt2beta']['use']:
        sc = inp.SNSPEC == 1; nsc = inp.SNSPEC == 0
        muA[sc],muAerr[sc] = salt2mu(x1=inp.x1[sc],x1err=inp.x1ERR[sc],c=inp.c[sc],cerr=inp.cERR[sc],mb=inp.mB[sc],mberr=inp.mBERR[sc],
                             cov_x1_c=inp.COV_x1_c[sc],cov_x1_x0=inp.COV_x1_x0[sc],cov_c_x0=inp.COV_c_x0[sc],
                             alpha=x[pardict['salt2alpha']['idx']],
                             beta=x[pardict['salt2beta']['idx']],
                             x0=inp.x0[sc],z=inp.zHD[sc])
        muA[nsc],muAerr[nsc] = salt2mu(x1=inp.x1[nsc],x1err=inp.x1ERR[nsc],c=inp.c[nsc],cerr=inp.cERR[nsc],mb=inp.mB[nsc],mberr=inp.mBERR[nsc],
                             cov_x1_c=inp.COV_x1_c[nsc],cov_x1_x0=inp.COV_x1_x0[nsc],cov_c_x0=inp.COV_c_x0[nsc],
                             alpha=x[pardict['salt2alpha']['idx']],
                             beta=x[pardict['salt2beta']['idx']]+x[pardict['salt2beta_poff']['idx']],
                             x0=inp.x0[nsc],z=inp.zHD[nsc])
    else: muA,muAerr = inp.mu[:],inp.muerr[:]


    return(muA,muAerr)


def twogausslike(x,inp=None,zcontrol=None,usescale=True,pardict=None,debug=False):

    if pardict['salt2beta_poff']['use']:
        muA,muAerr = getdatamu_poff(x,inp,pardict)
    else:
        muA,muAerr = getdatamu(x,inp,pardict)

    if pardict['salt2alpha_CC']['use'] and pardict['salt2beta_CC']['use']:
        muC,muCerr = getdatamu_CC(x,inp,pardict)
    else:
        muC,muCerr = inp.mu[:],inp.muerr[:]

    muB,muBerr = inp.mu[:],inp.muerr[:]
    # keep only the ones where invvars isn't messed up for muA
    muB,muBerr = muB[muAerr == muAerr],muBerr[muAerr == muAerr]
    muC,muCerr = muC[muAerr == muAerr],muCerr[muAerr == muAerr]
    zHD,PA,PL,snspec = inp.zHD[muAerr == muAerr],inp.PA[muAerr == muAerr],inp.PL[muAerr == muAerr],inp.SNSPEC[muAerr == muAerr]
    muA,muAerr = muA[muAerr == muAerr],muAerr[muAerr == muAerr]
    muC[muCerr != muCerr],muCerr[muCerr != muCerr] = muB[muCerr != muCerr],muBerr[muCerr != muCerr]

    # add in a shift
    if pardict['shift']['use']:
        PA[snspec != 1] += x[pardict['shift']['idx']]
        PA[PA > 1] = 1
        PA[PA < 0] = 0
    if usescale:
        PA[snspec != 1] = x[pardict['scaleA']['idx']]*PA[snspec != 1]/(1 - PA[snspec != 1] + x[pardict['scaleA']['idx']]*PA[snspec != 1])
        
    modeldict = zmodel(x,zcontrol,zHD,pardict)
    
    if pardict['lstep']['use']:
        if pardict['lstep_1']['use']:
            lsteplike = -(muA-modeldict['muAmodel']-(x[pardict['lstep']['idx']] + \
                                                         x[pardict['lstep_1']['idx']]*zHD))**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
                                                         np.log(PA*PL/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.)))
        else:
            lsteplike = -(muA-modeldict['muAmodel']-x[pardict['lstep']['idx']])**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
                np.log(PA*PL/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.)))

    else: lsteplike = np.zeros(len(muA)) - np.inf

    lnliketmp = logsumexp([-(muA-modeldict['muAmodel'])**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
                                np.log(PA*(1-PL)/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.))),
                            lsteplike,
                            -(muC-modeldict['muBmodel'])**2./(2.0*(muCerr**2.+modeldict['sigBmodel']**2.)) + \
                                np.log((1-PA)/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigBmodel']**2.+muBerr**2.)))],axis=0)
    lnlike = np.sum(lnliketmp) 

    if debug:
        if pardict['lstep']['use']:
            likeIa = np.sum(logsumexp([-(muA[PA == 1] - modeldict['muAmodel'][PA == 1])**2./(2.0*(muAerr[PA == 1]**2.+modeldict['sigAmodel'][PA == 1]**2.)) + \
                                            np.log(PA[PA == 1]*(1-PL[PA == 1])/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel'][PA == 1]**2. + \
                                                                                                             muBerr[PA == 1]**2.))),
                                       -(muA[PA == 1] - modeldict['muAmodel'][PA == 1] - x[pardict['lstep']['idx']])**2./(2.0*(muAerr[PA == 1]**2.+modeldict['sigAmodel'][PA == 1]**2.)) + \
                                            np.log(PA[PA == 1]*PL[PA == 1]/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel'][PA == 1]**2. + \
                                                                                                         muBerr[PA == 1]**2.)))],axis=0))
        else:
            likeIa = np.sum(logsumexp([-(muA[PA == 1] - modeldict['muAmodel'][PA == 1])**2./(2.0*(muAerr[PA == 1]**2.+modeldict['sigAmodel'][PA == 1]**2.)) + \
                                            np.log(PA[PA == 1]*(1-PL[PA == 1])/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel'][PA == 1]**2. + \
                                                                                                             muBerr[PA == 1]**2.)))],axis=0))

        print len(muA[PA == 1]),likeIa,x[pardict['popAstd']['idx']],x[pardict['scaleA']['idx']],x[pardict['salt2beta']['idx']]

    return(lnlike)

def threegausslike(x,inp=None,zcontrol=None,usescale=True,pardict=None,debug=False):

    if pardict['salt2beta_poff']['use']:
        muA,muAerr = getdatamu_poff(x,inp,pardict)
    else:
        muA,muAerr = getdatamu(x,inp,pardict)

    if pardict['salt2alpha_CC']['use'] and pardict['salt2beta_CC']['use']:
        muC,muCerr = getdatamu_CC(x,inp,pardict)
    else:
        muC,muCerr = inp.mu[:],inp.muerr[:]

    muB,muBerr = inp.mu[:],inp.muerr[:]
    # keep only the ones where invvars isn't messed up for muA
    muB,muBerr = muB[muAerr == muAerr],muBerr[muAerr == muAerr]
    muC,muCerr = muC[muAerr == muAerr],muCerr[muAerr == muAerr]
    zHD,PA,PL,snspec = inp.zHD[muAerr == muAerr],inp.PA[muAerr == muAerr],inp.PL[muAerr == muAerr],inp.SNSPEC[muAerr == muAerr]
    muA,muAerr = muA[muAerr == muAerr],muAerr[muAerr == muAerr]
    muC[muCerr != muCerr],muCerr[muCerr != muCerr] = muB[muCerr != muCerr],muBerr[muCerr != muCerr]

    # add in a shift
    if pardict['shift']['use']:
        PA[snspec != 1] += x[pardict['shift']['idx']]
        PA[PA > 1] = 1
        PA[PA < 0] = 0
    if usescale:
        PA[snspec != 1] = x[pardict['scaleA']['idx']]*PA[snspec != 1]/(1 - PA[snspec != 1] + x[pardict['scaleA']['idx']]*PA[snspec != 1])

    modeldict = zmodel(x,zcontrol,zHD,pardict)
    
    if pardict['lstep']['use']:
        if pardict['lstep_1']['use']:
            lsteplike = -(muA-modeldict['muAmodel']-(x[pardict['lstep']['idx']] + \
                                                         x[pardict['lstep_1']['idx']]*zHD))**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
                                                         np.log(PA*PL/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.)))
        else:
            lsteplike = -(muA-modeldict['muAmodel']-x[pardict['lstep']['idx']])**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
                np.log(PA*PL/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.)))

    else: lsteplike = np.zeros(len(muA)) - np.inf

    sum = logsumexp([-(muA-modeldict['muAmodel'])**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
                          np.log(PA*(1-PL)/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.))),
                      lsteplike,
                      -(muC-modeldict['muBmodel'])**2./(2.0*(muCerr**2.+modeldict['sigBmodel']**2.)) + \
                          np.log((1-PA)/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigBmodel']**2.+muBerr**2.))),
                      -(muC-modeldict['muB2model'])**2./(2.0*(muCerr**2.+modeldict['sigB2model']**2.)) + \
                          np.log((1-PA)/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigB2model']**2.+muBerr**2.)))],axis=0)

    if debug:
        likeIa = np.sum(logsumexp(
                [-(muA[PA == 1] - modeldict['muAmodel'][PA == 1])**2./(2.0*(muAerr[PA == 1]**2. + \
                                                                                modeldict['sigAmodel'][PA == 1]**2.)) + \
                      np.log(PA[PA == 1]*(1-PL[PA == 1])/(np.sqrt(2*np.pi)*\
                                                              np.sqrt(modeldict['sigAmodel'][PA == 1]**2. + \
                                                                          muBerr[PA == 1]**2.)))],axis=0))
        print len(muA[PA == 1]),likeIa,x[pardict['popAstd']['idx']],x[pardict['scaleA']['idx']],x[pardict['salt2beta']['idx']]

    return np.sum(sum)

def twogausslike_skew(x,inp=None,zcontrol=None,usescale=True,pardict=None,debug=False):

    if pardict['salt2beta_poff']['use']:
        muA,muAerr = getdatamu_poff(x,inp,pardict)
    else:
        muA,muAerr = getdatamu(x,inp,pardict)

    if pardict['salt2alpha_CC']['use'] and pardict['salt2beta_CC']['use']:
        muC,muCerr = getdatamu_CC(x,inp,pardict)
    else:
        muC,muCerr = inp.mu[:],inp.muerr[:]

    muB,muBerr = inp.mu[:],inp.muerr[:]
    # keep only the ones where invvars isn't messed up for muA
    muB,muBerr = muB[muAerr == muAerr],muBerr[muAerr == muAerr]
    muC,muCerr = muC[muAerr == muAerr],muCerr[muAerr == muAerr]
    zHD,PA,PL,snspec = inp.zHD[muAerr == muAerr],inp.PA[muAerr == muAerr],inp.PL[muAerr == muAerr],inp.SNSPEC[muAerr == muAerr]
    muA,muAerr = muA[muAerr == muAerr],muAerr[muAerr == muAerr]
    muC[muCerr != muCerr],muCerr[muCerr != muCerr] = muB[muCerr != muCerr],muBerr[muCerr != muCerr]

    modeldict = zmodel(x,zcontrol,zHD,pardict)
    
    # add in a shift
    if pardict['shift']['use']:
        PA[snspec != 1] += x[pardict['shift']['idx']]
        PA[PA > 1] = 1
        PA[PA < 0] = 0
    if usescale:
        PA[snspec != 1] = x[pardict['scaleA']['idx']]*PA[snspec != 1]/(1 - PA[snspec != 1] + x[pardict['scaleA']['idx']]*PA[snspec != 1])

    gaussA = -(muA-modeldict['muAmodel'])**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
        np.log(PA*(1-PL)/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.)))

    if pardict['lstep']['use']:
        if pardict['lstep_1']['use']:
            lsteplike = -(muA-modeldict['muAmodel']-(x[pardict['lstep']['idx']] + \
                                                         x[pardict['lstep_1']['idx']]*zHD))**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
                                                         np.log(PA*PL/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.)))
        else:
            lsteplike = -(muA-modeldict['muAmodel']-x[pardict['lstep']['idx']])**2./(2.0*(muAerr**2.+modeldict['sigAmodel']**2.)) + \
                np.log(PA*PL/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigAmodel']**2.+muBerr**2.)))

    else: lsteplike = np.zeros(len(muA)) - np.inf

    normB = (1-PA)/(np.sqrt(2*np.pi)*np.sqrt(modeldict['sigBmodel']**2.+muBerr**2.))
    gaussB = -(muC-modeldict['muBmodel'])**2./(2*(modeldict['sigBmodel']**2.+muCerr**2.))
    skewB = 1 + erf(modeldict['skewBmodel']*(muB-modeldict['muBmodel'])/np.sqrt(2*(modeldict['sigBmodel']**2.+muBerr**2.)))

    skewgaussB = gaussB + np.log(normB*skewB)
    lnlike = np.sum(logsumexp([gaussA,lsteplike,skewgaussB],axis=0))
    if debug:
        likeIa = np.sum(logsumexp([-(muA[PA == 1] - modeldict['muAmodel'][PA == 1])**2./ \
                                        (2.0*(muAerr[PA == 1]**2.+modeldict['sigAmodel'][PA == 1]**2.)) + \
                                        np.log(PA[PA == 1]*(1-PL[PA == 1])/(np.sqrt(2*np.pi)*\
                                                                                       np.sqrt(modeldict['sigAmodel'][PA == 1]**2. + \
                                                                                                   muBerr[PA == 1]**2.)))],axis=0))
        print len(muA[PA == 1]),likeIa,x[pardict['salt2beta']['idx']]

    return(lnlike)

def lnprior(theta,pardict=None):

    p_theta = 1.0
    for t,i in zip(theta,range(len(theta))):
        prior_mean,prior_std,lbound,ubound,key = getpriors(i,pardict)
        # don't allow distance prior
        if key != 'popAmean':
            p_theta += norm.logpdf(t,prior_mean,prior_std)

        if key == 'scaleA' and pardict['scaleA']['use'] and pardict['scaleA']['idx'] == i:
            if t < 0: return -np.inf
  
#        if t < lbound or t > ubound:
#            return -np.inf

    return(p_theta)

def getpriors(idx,pardict):
    for k in pardict.keys():
        if hasattr(pardict[k]['idx'],"__len__"):
            if idx in pardict[k]['idx']:
                return(pardict[k]['prior_mean'][pardict[k]['idx'] == idx][0],
                       pardict[k]['prior_std'],
                       pardict[k]['bounds'][0][pardict[k]['idx'] == idx][0],
                       pardict[k]['bounds'][1][pardict[k]['idx'] == idx][0],k)
        else:
            if idx == pardict[k]['idx']:
                return(pardict[k]['prior_mean'],
                       pardict[k]['prior_std'],
                       pardict[k]['bounds'][0],
                       pardict[k]['bounds'][1],k)

    return()

def getparval(idx,pardict,valkey):
    for k in pardict.keys():
        if hasattr(pardict[k]['idx'],"__len__"):
            if hasattr(pardict[k][valkey],"__len__"):
                if idx in pardict[k]['idx']:
                    return(pardict[k][valkey][pardict[k]['idx'] == idx])
            else:
                    return(pardict[k][valkey])
        else:
            if idx == pardict[k]['idx']:
                return(pardict[k][valkey])

    return()

def getpar(idx,pardict):
    for k in pardict.keys():
        if hasattr(pardict[k]['idx'],"__len__"):
            if idx in pardict[k]['idx']:
                return(k)
        else:
            if idx == pardict[k]['idx']:
                return(k)

    return()


def lnprob(theta,inp=None,zcontrol=None,
           pardict=None,debug=False):

    if pardict['popB2mean']['use']:
        lnlikefunc = lambda *args: threegausslike(*args)
    elif pardict['skewB']['use']:
        lnlikefunc = lambda *args: twogausslike_skew(*args)
    else:
        lnlikefunc = lambda *args: twogausslike(*args)

    lp = lnprior(theta,pardict)

    if not np.isfinite(lp) or np.isnan(lp):
        return -np.inf

    if pardict['scaleA']['use']: usescale = True
    else: usescale = False
    post = lp + lnlikefunc(theta,inp,zcontrol,usescale,pardict,debug)

    if post != post: return -np.inf
    else: return post


def gauss(x,x0,sigma):
    return(normpdf(x,x0,sigma))

def normpdf(x, mu, sigma):
    u = (x-mu)/np.abs(sigma)
    y = (1/(np.sqrt(2*np.pi)*np.abs(sigma)))*np.exp(-u*u/2)
    return y

def covmat(samples):
    cov_shape = np.shape(samples)[1]
    chain_len = np.shape(samples)[0]
    covmat = np.zeros([cov_shape,cov_shape])
    for i in range(cov_shape):
        for j in range(cov_shape):
            covmat[j,i] = np.sum((samples[:,j]-np.mean(samples[:,j]))*(samples[:,i]-np.mean(samples[:,i])))/chain_len
    return(covmat)

def weighted_avg_and_std(values, weights):
    import numpy
    average = numpy.average(values, weights=weights)
    variance = numpy.average((values-average)**2, weights=weights)  # Fast and numerically precise
    return (average, numpy.sqrt(variance))

def salt2mu(x1=None,x1err=None,
            c=None,cerr=None,
            mb=None,mberr=None,
            cov_x1_c=None,cov_x1_x0=None,cov_c_x0=None,
            alpha=None,beta=None,
            M=None,x0=None,sigint=None,z=None,peczerr=0.00083):

    sf = -2.5/(x0*np.log(10.0))
    cov_mb_c = cov_c_x0*sf
    cov_mb_x1 = cov_x1_x0*sf
    mu_out = mb + x1*alpha - beta*c + 19.36
    invvars = 1.0 / (mberr**2.+ alpha**2. * x1err**2. + beta**2. * cerr**2. + \
                         2.0 * alpha * (cov_x1_x0*sf) - 2.0 * beta * (cov_c_x0*sf) - \
                         2.0 * alpha*beta * (cov_x1_c) )

    zerr = peczerr*5.0/np.log(10)*(1.0+z)/(z*(1.0+z/2.0))
    muerr_out = np.sqrt(1/invvars + zerr**2. + 0.055**2.*z**2.)
    if sigint: muerr_out = np.sqrt(muerr_out**2. + sigint**2.)
    return(mu_out,muerr_out)

def salt2mu_aberr(x1=None,x1err=None,
                  c=None,cerr=None,
                  mb=None,mberr=None,
                  cov_x1_c=None,cov_x1_x0=None,cov_c_x0=None,
                  alpha=None,beta=None,
                  alphaerr=None,betaerr=None,
                  M=None,x0=None,sigint=None,z=None,peczerr=0.00083):
    from uncertainties import ufloat, correlated_values, correlated_values_norm
    alphatmp,betatmp = alpha,beta
    alpha,beta = ufloat(alpha,alphaerr),ufloat(beta,betaerr)

    sf = -2.5/(x0*np.log(10.0))
    cov_mb_c = cov_c_x0*sf
    cov_mb_x1 = cov_x1_x0*sf

    mu_out,muerr_out = np.array([]),np.array([])
    for i in range(len(x1)):

        covmat = np.array([[mberr[i]**2.,cov_mb_x1[i],cov_mb_c[i]],
                           [cov_mb_x1[i],x1err[i]**2.,cov_x1_c[i]],
                           [cov_mb_c[i],cov_x1_c[i],cerr[i]**2.]])
        mb_single,x1_single,c_single = correlated_values([mb[i],x1[i],c[i]],covmat)

        mu = mb_single + x1_single*alpha - beta*c_single + 19.36
        if sigint: mu = mu + ufloat(0,sigint)
        zerr = peczerr*5.0/np.log(10)*(1.0+z[i])/(z[i]*(1.0+z[i]/2.0))

        mu = mu + ufloat(0,np.sqrt(zerr**2. + 0.055**2.*z[i]**2.))
        mu_out,muerr_out = np.append(mu_out,mu.n),np.append(muerr_out,mu.std_dev)

    return(mu_out,muerr_out)

if __name__ == "__main__":
    usagestring="""An implementation of the BEAMS method (Kunz, Bassett, & Hlozek 2006).
Uses Bayesian methods to estimate the mags of a sample with contaminants.  This version
follows Betoule et al. (2014) and sets a series of distance modulus control points, 
simultaneously finding the distance moduli at each of these points via MCMC, and prints 
the full covariance matrix.

Takes a
parameter file or command line options, and a file with the following header/columns:

# PA z mu mu_err
<PA_1> <z> <resid_1> <resid_err_1>
<PA_2> <z> <resid_2> <resid_err_2>
<PA_3> <z> <resid_3> <resid_err_3>
.......

The PA column is the prior probability that a data point belongs to population A, P(A).
Column 2 is some sort of de-trended magnitude measurement (i.e. Hubble residuals), and
column 3 is the uncertainties on those measurements.

Can specify or fix, with priors:

1. The mean and standard deviation of the population of interest
2. The mean and standard deviation of the contaminant population
3. The fraction of contaminants

USAGE: dobeams.py -p param_file -i input_file [options]

examples:
"""

    import exceptions
    import os
    import optparse
    import ConfigParser

    beam = BEAMS()

    # read in the options from the param file and the command line
    # some convoluted syntax here, making it so param file is not required
    parser = beam.add_options(usage=usagestring)
    options,  args = parser.parse_args()
    if options.paramfile:
        config = ConfigParser.ConfigParser()
        config.read(options.paramfile)
    else: config=None
    parser = beam.add_options(usage=usagestring,config=config)
    options,  args = parser.parse_args()


    beam.options = options
    beam.verbose = options.verbose
    beam.clobber = options.clobber

    from scipy.optimize import minimize
    import emcee

    beam.main(options.inputfile)

