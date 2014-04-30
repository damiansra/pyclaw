#!/usr/bin/env python
# encoding: utf-8
r"""
Controller for basic computation and plotting setup.

This module defines the Pyclaw controller class.  It can be used to perform
simulations in a convenient manner similar to that available in previous
versions of Clawpack, i.e. with output_style and
output time specification.  It also can be used to set up easy plotting and 
running of compiled fortran binaries.
"""

import logging
import sys
import os
import copy

from .solver import Solver
from .util import FrameCounter
from .util import LOGGING_LEVELS

class Controller(object):
    r"""Controller for pyclaw simulation runs and plotting
            
    :Initialization:
    
        Input: None
    
    :Examples:

        >>> import clawpack.pyclaw as pyclaw
        >>> x = pyclaw.Dimension('x',0.,1.,100)
        >>> domain = pyclaw.Domain((x))
        >>> state = pyclaw.State(domain,3,2)
        >>> claw = pyclaw.Controller()
        >>> claw.solution = pyclaw.Solution(state,domain)
        >>> claw.solver = pyclaw.ClawSolver1D()
    """

    def __getattr__(self, key):
        if key in ('t','num_eqn','mp','mF','q','p','F','aux','capa',
                   'problem_data','num_aux',
                   'num_dim', 'p_centers', 'p_edges', 'c_centers', 'c_edges',
                   'num_cells', 'lower', 'upper', 'delta', 'centers', 'edges',
                   'gauges', 'num_eqn', 'num_aux', 'grid', 'problem_data'):
            return self._get_solution_attribute(key)
        else:
            raise AttributeError("'Controller' object has no attribute '"+key+"'")

    def _get_solution_attribute(self, name):
        r"""
        Return solution attribute
        
        :Output:
         - (id) - Value of attribute from ``solution``
        """
        return getattr(self.solution,name)
 

    #  ======================================================================
    #   Property Definitions
    #  ======================================================================
    @property
    def verbosity(self):
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value):
        self._verbosity = value
        # Only adjust console logger; leave file logger alone
        self.logger.handlers[1].setLevel(LOGGING_LEVELS[value])

    @property
    def outdir_p(self):
        r"""(string) - Directory to use for writing derived quantity files"""
        return os.path.join(self.outdir,'_p')
    @property
    def F_path(self):
        r"""(string) - Full path to output file for functionals"""
        return os.path.join(self.outdir,self.F_file_name+'.txt')

    #  ======================================================================
    #   Initialization routines
    #  ======================================================================
    def __init__(self):
        r"""
        Initialization routine for a Controller object.
        
        See :class:`Controller` for full documentation.
        """
        
        import numpy as np

        self.viewable_attributes = ['xdir','rundir','outdir','overwrite',
                        'xclawcmd','xclawout','xclawerr','runmake','savecode',
                        'solver','keep_copy','write_aux_init',
                        'write_aux_always','output_format',
                        'output_file_prefix','output_options','num_output_times',
                        'output_style','verbosity',
                        'output_handler','output_clobber']
        r"""(list) - Viewable attributes of the `:class:`~pyclaw.controller.Controller`"""

        # Global information for running and/or plotting
        self.xdir = os.getcwd()
        r"""(string) - Executable path, executes xclawcmd in xdir"""
        self.rundir = os.getcwd()
        r"""(string) - Directory to run from (containing \*.data files), uses 
        \*.data from rundir"""
        self.outdir = os.getcwd()+'/_output'
        r"""(string) - Output directory, directs output files to outdir"""
        self.overwrite = True
        r"""(bool) - Ok to overwrite old result in outdir, ``default = True``"""
        self.xclawcmd = 'xclaw'
        r"""(string) - Command to execute (if using fortran), defaults to xclaw or
        xclaw.exe if cygwin is being used (which it checks vis sys.platform)"""
        if sys.platform == 'cygwin':
            self.xclawcmd = 'xclaw.exe'

        self.start_frame = 0
        r"""(int) - Frame at which begins, ``default = 0``"""
        self.xclawout = None
        r"""(string) - Where to write timestep messages"""
        self.xclawerr = None
        r"""(string) - Where to write error messages"""
        self.runmake = False
        r"""(bool) - Run make in xdir before xclawcmd"""
        self.savecode = False
        r"""(bool) - Save a copy of \*.f files in outdir"""
        
        self.setplot = None
        r""" (string) - Name of setplot py file ``default = None``"""

        # Solver information
        self.solution = None
        self.solver = None
        r"""(:class:`~pyclaw.solver.Solver`) - Solver object"""
        
        # Output parameters for run convenience method
        self.keep_copy = False 
        r"""(bool) - Keep a copy in memory of every output time, 
        ``default = False``"""
        self.frames = []
        r"""(list) - List of saved frames if ``keep_copy`` is set to ``True``"""
        self.write_aux_init = False
        r"""(bool) - Write out initial auxiliary array, ``default = False``"""
        self.write_aux_always = False
        r"""(bool) - Write out auxiliary array at every time step, 
        ``default = False``"""
        self.output_handler = 'pyclaw'
        r"""(string) - Method to output data. Available methods are: 'petsc', 'serial', None.
        ``default = 'serial'``"""
        self.output_format = 'ascii'
        r"""(string) - Format to output data, if this is None, no output is performed.
        See _pyclaw_io for more info on available formats.  ``default = 'ascii'``"""
        self.output_file_prefix = None
        r"""(string) - File prefix to be appended to output files, 
        ``default = None``"""
        self.output_clobber = True
        r"""(bool) - Whether to overwrite files in output directory, ``default = True``"""
        self.output_options = {}
        r"""(dict) - output options to be passed to hdf5/netcdf in serial method"""
        
        self.logger = logging.getLogger('pyclaw.controller')

        # Classic output parameters, used in run convenience method
        self.tfinal = 1.0
        r"""(float) - Final time output, ``default = 1.0``"""
        self.output_style = 1
        r"""(int) - Time output style, ``default = 1``"""
        self.verbosity = 3
        r"""(int) - Level of output to screen; ``default = 3``"""
        self.num_output_times = 10                  # Outstyle 1 defaults
        r"""(int) - Number of output times, only used with ``output_style = 1``,
        ``default = 10``"""
        self.out_times = np.linspace(0.0,self.tfinal,self.num_output_times
                                     -self.start_frame) # Outstyle 2
        r"""(int) - Output time list, only used with ``output_style = 2``,
        ``default = numpy.linspace(0.0,tfinal,num_output_times)``"""
        
        self.nstepout = 1               # Outstyle 3 defaults
        r"""(int) - Number of steps between output, only used with 
        ``output_style = 3``, ``default = 1``"""
        
        # Data objects
        self.plotdata = None
        r"""(:class:`~visclaw.data.ClawPlotData`) - An instance of a 
        :class:`~visclaw.data.ClawPlotData` object defining the 
        objects plot parameters."""
        
        # Derived quantity p
        self.file_prefix_p = 'claw_p'
        r"""(string) - File prefix to be prepended to derived quantity output files"""
        self.compute_p = None
        r"""(function) - function that computes derived quantities"""
        
        # functionals
        self.compute_F = None
        r"""(function) - Function that computes density of functional F"""
        self.F_file_name = 'F'
        r"""(string) - Name of text file containing functionals"""

    # ========== Access methods ===============================================
    def __str__(self):        
        output = "Controller attributes:\n"
        for attr in self.viewable_attributes:
            value = getattr(self,attr)
            output = output + "  %s = %s \n" % (attr,value)
        output = output + '\n'
        if self.plotdata is not None:
            output = output + "  Data "+str(self.plotdata)+"\n"
        if self.solver is not None:
            output = output + "  Solver "+str(self.solver)+"\n"
        if len(self.frames) > 0:
            output = output + "  Frames \n"
            for frame in self.frames:
                output = output + "    " + str(frame) + "\n"
        return output
        
    # ========== Properties ==================================================
    
    def check_validity(self):
        r"""Check that the controller has been properly set up and is ready to run.

            Also checks validity of the solver, solution and states.
        """
        # Check to make sure we have a valid solver to use
        if self.solver is None:
            raise Exception("No solver set in controller.")
        if not isinstance(self.solver,Solver):
            raise Exception("Solver is not of correct type.")
        valid, reason = self.solver.is_valid()
        if not valid:
            raise Exception("The solver failed to initialize properly because "+reason) 
            
        # Check to make sure the initial solution is valid
        if not self.solution.is_valid():
            raise Exception("Initial solution is not valid.")
        if not all([state.is_valid() for state in self.solution.states]):
            raise Exception("Initial states are not valid.")
        
 
    # ========== Plotting methods ============================================        
    def set_plotdata(self):
        from clawpack.visclaw import data
        from clawpack.visclaw import frametools
        plotdata = data.ClawPlotData()
        plotdata.setplot = self.setplot
        self.plotdata = frametools.call_setplot(self.setplot,plotdata)
        plotdata._mode = 'iplotclaw'

    def load_frame(self,frame_number):
        try: 
            return self.frames[frame_number]
        except IndexError:
            print "Cannot plot frame %s; only %s frames available" % (frame_number, len(self.frames))

    def plot_frame(self, frame):
        if self.plotdata is None:
            self.set_plotdata()

        if frame is not None:
            frameno = self.frames.index(frame)
            from clawpack.visclaw import frametools
            frametools.plot_frame(frame, self.plotdata, frameno=frameno)

    def plot(self):
        """Plot from memory."""
        if len(self.frames) == 0:  # No frames to plot
            print "No frames to plot.  Did you forget to run, or to set keep_copy=True?"
            return

        from clawpack.visclaw import iplot

        if self.plotdata is None:
            self.set_plotdata()

        ip = iplot.Iplot(self.load_frame,self.plot_frame)
        ip.plotloop()

    # ========== Solver convenience methods ==================================
    def run(self):
        r"""
        Convenience routine that will evolve solution based on the 
        traditional clawpack output and run parameters.
        
        This function uses the run parameters and solver parameters to evolve
        the solution to the end time specified in run_data, outputting at the
        appropriate times.
        
        :Input:
            None
            
        :Ouput:
            (dict) - Return a dictionary of the status of the solver.
        """
        import numpy as np

        if self.solver is None or self.solution is None:
            raise Exception('To run, a Controller must have a Solver and a Solution.')

        self.start_frame = self.solution.start_frame
        if len(self.solution.patch.grid.gauges)>0:
            self.solution.patch.grid.setup_gauge_files(self.outdir)
        frame = FrameCounter()

        frame.set_counter(self.start_frame)

        if not self.solver._is_set_up:
            self.solver.setup(self.solution)
            self.solver.dt = self.solver.dt_initial

        self.check_validity()

        # Write initial gauge values
        self.solver.write_gauge_values(self.solution)

        # Output styles
        if self.output_style == 1:
            output_times = np.linspace(self.solution.t,
                    self.tfinal,self.num_output_times+1)
        elif self.output_style == 2:
            output_times = self.out_times
        elif self.output_style == 3:
            output_times = np.ones((self.num_output_times+1
                                    -self.start_frame))
        else:
            raise Exception("Invalid output style %s" % self.output_style)  

        if len(output_times) == 0:
            print "No valid output times; halting."
            if self.t == self.tfinal:
                print "Simulation has already reached tfinal."
            return None

        # Output and save initial frame

        if self.keep_copy:
            self.frames.append(copy.deepcopy(self.solution))
        if self.output_handler==None or self.output_format==None:
            pass
        else:
            if os.path.exists(self.outdir) and self.output_clobber==False:
                raise Exception("Refusing to overwrite existing output data. \
                 \nEither delete/move the directory or set controller.overwrite=True.")
            if self.compute_p is not None:
                self.compute_p(self.solution.state)
                self.solution.write(frame = frame,
                                        path = self.outdir_p,
                                        file_prefix = self.file_prefix_p,
                                        io_handler = self.output_handler,
                                        file_format = self.output_format,
                                        clobber = self.output_clobber,
                                        write_aux = False,
                                        write_p = True,
                                        options = self.output_options)

            write_aux = (self.write_aux_always or self.write_aux_init)
            self.solution.write(frame = frame,
                                path = self.outdir,
                                file_prefix = self.output_file_prefix,
                                io_handler = self.output_handler,
                                file_format = self.output_format,
                                clobber = self.output_clobber,
                                write_aux = write_aux,
                                write_p = False,
                                options = self.output_options)

        self.write_F('w')

        self.log_info("Solution %s computed for time t=%f" % 
                        (frame,self.solution.t) )

        for t in output_times[1:]:                
            if self.output_style < 3:
                status = self.solver.evolve_to_time(self.solution,t)
            else:
                # Take nstepout steps and output
                for n in xrange(self.nstepout):
                    status = self.solver.evolve_to_time(self.solution)
            frame.increment()
            if self.keep_copy:
                # Save current solution to dictionary with frame as key
                self.frames.append(copy.deepcopy(self.solution))
            if self.output_handler==None or self.output_format==None:
                pass
            else:
                if self.compute_p is not None:
                    self.compute_p(self.solution.state)
                    self.solution.write(frame=frame,
                                        path = self.outdir,
                                        file_prefix = self.file_prefix_p,
                                        io_handler = self.output_handler,
                                        file_format = self.output_format,
                                        clobber = self.output_clobber,
                                        write_aux = False,
                                        write_p = True,
                                        options = self.output_options)
                
                self.solution.write(frame=frame,
                                    path = self.outdir,
                                    file_prefix = self.output_file_prefix,
                                    io_handler = self.output_handler,
                                    file_format = self.output_format,
                                    clobber = self.output_clobber,
                                    write_aux = self.write_aux_always,
                                    write_p = False,
                                    options = self.output_options)
            self.write_F()

            self.log_info("Solution %s computed for time t=%f"
                % (frame,self.solution.t))
            for gfile in self.solution.state.grid.gauge_files: 
                gfile.flush()
            
        for gfile in self.solution.state.grid.gauge_files: gfile.close()

        self.solution._start_frame = len(self.frames)

        # Return the current status of the solver
        return status
    
    # ========== Advanced output methods ==================================

    def write_F(self,mode='a'):
        if self.compute_F is not None:
            self.compute_F(self.solution.state)
            F = [0]*self.solution.state.mF
            for i in xrange(self.solution.state.mF):
                F[i] = self.solution.state.sum_F(i)
            if self.is_proc_0():
                t=self.solution.t
                F_file = open(self.F_path,mode)
                F_file.write(str(t)+' '+' '.join(str(j) for j in F) + '\n')
                F_file.close()
    
    def is_proc_0(self):
        return True

    def log_info(self, str):
        self.logger.info(str)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
