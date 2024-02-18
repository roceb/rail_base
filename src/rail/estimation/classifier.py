"""
Abstract base classes defining classifiers.
"""

import gc
from rail.core.data import QPHandle, TableHandle, ModelHandle, Hdf5Handle
from rail.core.stage import RailStage


class CatClassifier(RailStage):  #pragma: no cover
    """The base class for assigning classes to catalogue-like table.

    Classifier uses a generic "model", the details of which depends on the sub-class.

    CatClassifier take as "input" a catalogue-like table, assign each object into
    a tomographic bin, and provide as "output" a tabular data which can be appended 
    to the catalogue.
    """
    
    name='CatClassifier'
    config_options = RailStage.config_options.copy()
    config_options.update(chunk_size=10000, hdf5_groupname=str)
    inputs = [('model', ModelHandle),
              ('input', TableHandle)]
    outputs = [('output', TableHandle)]
    
    def __init__(self, args, comm=None):
        """Initialize Classifier"""
        RailStage.__init__(self, args, comm=comm)
        self._output_handle = None
        self.model = None
        if not isinstance(args, dict):  #pragma: no cover
            args = vars(args)
        self.open_model(**args)
        
    
    def open_model(self, **kwargs):
        """Load the model and/or attach it to this Classifier

        Parameters
        ----------
        model : `object`, `str` or `ModelHandle`
            Either an object with a trained model,
            a path pointing to a file that can be read to obtain the trained model,
            or a `ModelHandle` providing access to the trained model.

        Returns
        -------
        self.model : `object`
            The object encapsulating the trained model.
        """
        model = kwargs.get('model', None)
        if model is None or model == 'None':
            self.model = None
            return self.model
        if isinstance(model, str):
            self.model = self.set_data('model', data=None, path=model)
            self.config['model'] = model
            return self.model
        if isinstance(model, ModelHandle):
            if model.has_path:
                self.config['model'] = model.path
        self.model = self.set_data('model', model)
        return self.model
        
        
    def classify(self, input_data):
        """The main run method for the classifier, should be implemented
        in the specific subclass.

        This will attach the input_data to this `CatClassifier`
        (for introspection and provenance tracking).

        Then it will call the run() and finalize() methods, which need to
        be implemented by the sub-classes.

        The run() method will need to register the data that it creates to this Classifier
        by using `self.add_data('output', output_data)`.

        Finally, this will return a TableHandle providing access to that output data.

        Parameters
        ----------
        input_data : `dict`
            A dictionary of all input data

        Returns
        -------
        output: `dict`
            Class assignment for each galaxy.
        """
        self.set_data('input', input_data)
        self.run()
        self.finalize()
        return self.get_handle('output')
    

    
class PZClassifier(RailStage):
    """The base class for assigning classes (tomographic bins) to per-galaxy PZ estimates

    PZClassifier take as "input" a `qp.Ensemble` with per-galaxy PDFs, and
    provide as "output" a tabular data which can be appended to the catalogue.
    """
    
    name='PZClassifier'
    config_options = RailStage.config_options.copy()
    config_options.update(chunk_size=10000)
    inputs = [('input', QPHandle)]
    outputs = [('output', Hdf5Handle)]
    
    def __init__(self, args, comm=None):
        """Initialize Classifier"""
        RailStage.__init__(self, args, comm=comm)
        
        self._output_handle = None
        

    def classify(self, input_data):
        """The main run method for the classifier, should be implemented
        in the specific subclass.

        This will attach the input_data to this `PZClassifier`
        (for introspection and provenance tracking).

        Then it will call the run() and finalize() methods, which need to
        be implemented by the sub-classes.

        The run() method will need to register the data that it creates to this Classifier
        by using `self.add_data('output', output_data)`.

        Finally, this will return a TableHandle providing access to that output data.

        TODO: rewrite for parallelized version

        Parameters
        ----------
        input_data : `qp.Ensemble`
            Per-galaxy p(z), and any ancilary data associated with it

        Returns
        -------
        output: `dict`
            Class assignment for each galaxy.
        """
        self.set_data('input', input_data)
        self.run()
        self.finalize()
        return self.get_handle('output')
    

    # finalize run
    def _finalize_run(self):
        self._output_handle.finalize_write()
    
    # process chunk
    def _process_chunk(self, start, end, data, first):
        raise NotImplementedError(f"{self.name}._process_chunk is not implemented")  # pragma: no cover
    
    # do chunk output
    def _do_chunk_output(self, class_id, start, end, first):
        if first:
            self._output_handle = self.add_handle('output', data=class_id)
            self._output_handle.initialize_write(self._input_length, communicator=self.comm)
        self._output_handle.set_data(class_id, partial=True)
        self._output_handle.write_chunk(start, end)

    # run
    def run(self):
        test_data = self.get_data('input')
        
        iterator = self.input_iterator('input') # calling RailStage's input_iterator here
        first = True
        
        for s, e, test_data in iterator:
            #print(f"Process {self.rank} running estimator on chunk {s} - {e}")
            self._process_chunk(s, e, test_data, first)
            first = False
            # Running garbage collection manually seems to be needed
            # to avoid memory growth for some estimators
            gc.collect()
        self._finalize_run()
