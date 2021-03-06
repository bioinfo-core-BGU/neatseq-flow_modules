# -*- coding: UTF-8 -*-
""" 
``BUSCO``
-----------------------------------------------------------------
:Authors: Menachem Sklarz
:Affiliation: Bioinformatics core facility
:Organization: National Institute of Biotechnology in the Negev, Ben Gurion University.

A class that defines a module for running ``BUSCO``.

BUSCO searches for predefined sequences in an assembly. See `the BUSCO website <https://busco.ezlab.org/>`_.

This module creates scripts for running BUSCO on a fasta file against a BUSCO lineage database.

The lineage can be specified in two ways:

1. Specify the path to the lineage file with the ``--lineage`` redirected argument.
2. Specify the URL of the database (*e.g.* http://busco.ezlab.org/v2/datasets/eukaryota_odb9.tar.gz). The file will be downloaded and unzipped.

Requires
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
* fasta files in one of the following slots for sample-wise BUSCO:

    * ``sample_data[<sample>]["fasta.nucl"]``
    * ``sample_data[<sample>]["fasta.prot"]``

* or fasta files in one of the following slots for project-wise BUSCO:

    * ``sample_data["fasta.nucl"]``
    * ``sample_data["fasta.prot"]``
    
Output:
~~~~~~~~~~~~~

* Stores output directory in:

    * self.sample_data[<sample>]["BUSCO"] (``scope = sample``)
    * self.sample_data["project_data"]["BUSCO"] (``scope = project``)

Parameters that can be set        
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. csv-table:: 
    :header: "Parameter", "Values", "Comments"

    "scope", "``sample`` | ``project``", "Use sample of project scope fasta file."
    "get_lineage", "", "Path to one of the lineages to download from https://busco.ezlab.org/frame_wget.html. Will be downloaded, unzipped and used if no --lineage is passed."

    
Lines for parameter file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run BUSCO on project-scope fasta file, using a pre-downloaded BUSCO database::

    BUSCO1:
        module:             BUSCO
        base:               Trinity_assembl
        script_path:        {Vars.paths.BUSCO} 
        scope:              project
        redirects:
            --mode:         transcriptome
            --lineage:      {Vars.databases.BUSCO}
            --cpu:          65
            --force:
            --restart:
            
Run BUSCO on project-scope fasta file, including downloading the BUSCO database::

    BUSCO1:
        module:             BUSCO
        base:               Trinity_assembl
        script_path:        {Vars.paths.BUSCO}
        scope:              project
        get_lineage:        http://busco.ezlab.org/v2/datasets/eukaryota_odb9.tar.gz
        redirects:
            --mode:         transcriptome
            --cpu:          65
            --force:
            --restart:


References
~~~~~~~~~~~~~~~~~~~~~~~~~~~~


"""



import os
import sys
import re
from neatseq_flow.PLC_step import Step,AssertionExcept


__author__ = "Menachem Sklarz"
__version__ = "1.6.0"


class Step_BUSCO(Step):

    
    def step_specific_init(self):
        self.shell = "bash"      # Can be set to "bash" by inheriting instances
        self.file_tag = "BUSCO"
        
        
        if "scope" not in self.params:
            raise AssertionExcept("Please specify a 'scope': Either 'sample' or 'project'.")
        
        for redir2remove in ["-i", "--in", "-o", "--out", "-t", "--tmp"]:
            if redir2remove in self.params["redir_params"]:
                del self.params["redir_params"][redir2remove]
                self.write_warning("You are not supposed to specify %s in redirects. We set it automatically" % redir2remove)
        
        # Transfering redirected "-m" into "--mode"
        if "-m" in self.params["redir_params"]:
            self.params["redir_params"]["--mode"] = self.params["redir_params"]["-m"]
            del self.params["redir_params"]["-m"]
        # Checking --mode is legitimate (is udes to choose fasta.prot or fasta.nucl
        if "--mode" not in self.params["redir_params"] and "-m" not in self.params["redir_params"]:
            raise AssertionExcept("""
You must specify a 'mode': 
- geno or genome, for genome assemblies (DNA)
- tran or transcriptome, for transcriptome assemblies (DNA)
- prot or proteins, for annotated gene sets (protein)\n\n""")
        
                
    def step_sample_initiation(self):
        """ A place to do initiation stages following setting of sample_data
            Here you should do testing for dependency output. These will NOT exist at initiation of this instance. They are set only following sample_data updating
        """

        if self.params["redir_params"]["--mode"] in ['geno', 'genome', 'tran', 'transcriptome']:
            self.type = "nucl"
        elif self.params["redir_params"]["--mode"] in ['prot', 'proteins']:
            self.type = "prot"
        else:
            raise AssertionExcept("The value you passed to --mode ({mode}) is not a valid value".
                                  format(mode=self.params["redir_params"]["--mode"]))

        if self.params["scope"] == "sample":
            # Check that "fasta" and "assembly" exist (signs that trinity has been executed)
            for sample in self.sample_data["samples"]:
                if ("fasta.%s" % self.type) not in self.sample_data[sample]:
                    raise AssertionExcept("It seems there is no sample-wide %s fasta file." % self.type, sample)
        elif self.params["scope"] == "project":
            if ("fasta.%s" % self.type) not in self.sample_data["project_data"]:
                raise AssertionExcept("It seems there is no project-wide %s fasta file." % self.type)
        else:
            raise AssertionExcept("'scope' must be either 'sample' or 'project'.")


    def create_spec_wrapping_up_script(self):
        """ Add stuff to check and agglomerate the output data
        """
        
        pass

    def create_spec_preliminary_script(self):
        """ Add script to run BEFORE all other steps
        """

        if "get_lineage" in self.params:

            use_dir = self.local_start(self.base_dir)

            self.script = """
# Moving into output location
cd {use_dir} 

wget {lineage}
tar zxvf {lineage_loc}

cd -
            """.format(use_dir=use_dir,
                       lineage=self.params["get_lineage"],
                       lineage_loc=os.path.basename(self.params["get_lineage"]))

            try:
                lineage = re.match("(.*)\.tar\.gz", os.path.basename(self.params["get_lineage"]))
                lineage = use_dir + lineage.group(1)
            except AttributeError as attrerr:
                raise AssertionExcept("Error with supplied lineage path ({lineage}".format(lineage=self.params["get_lineage"]))
            # Store results to fasta and assembly slots:
            self.sample_data["project_data"]["BUSCO.lineage"] = lineage
            # Move all files from temporary local dir to permanent base_dir
            self.local_finish(use_dir, self.base_dir)  # Sees to copying local files to final destination (and other stuff)

    def build_scripts(self):
    
        # Set list of samples to go over. Either self.sample_data["samples"] for sample scope
        # or ["project_data"] for project scope
        if self.params["scope"] == "project":
            sample_list = ["project_data"]
        elif self.params["scope"] == "sample":
            sample_list = self.sample_data["samples"]
        else:
            raise AssertionExcept("'scope' must be either 'sample' or 'project'")

        for sample in sample_list:  # Getting list of samples out of samples_hash

        # Name of specific script:
            self.spec_script_name = self.set_spec_script_name(sample)
            self.script = ""

            # Make a dir for the current sample:
            sample_dir = self.make_folder_for_sample(sample)

            # This line should be left before every new script. It sees to local issues.
            # Use the dir it returns as the base_dir for this step.
            use_dir = self.local_start(sample_dir)

            self.script += "# Moving into output location\n"
            self.script += "cd %s \n\n" % use_dir
            
            self.script += self.get_script_const()

            # The results will be put in data/step_name/name/Title
            self.script += "--out %s \\\n\t" % sample
            self.script += "--in %s \\\n\t"  % self.sample_data[sample]["fasta.%s" % self.type]
            self.script += "--tmp %s \\\n\t"  % os.path.join(use_dir,"tmp")
            
            if "--lineage" not in self.params["redir_params"]:
                if "BUSCO.lineage" in self.sample_data["project_data"]:
                    self.script += "--lineage %s \\\n\t" % self.sample_data["project_data"]["BUSCO.lineage"]
                else:
                    raise AssertionExcept("Please supply a lineage, either via redirects (--lineage) or via 'get_lineage'")

            self.script = self.script.rstrip("\\\n\t")

            # Store results to fasta and assembly slots:
            self.sample_data[sample]["BUSCO"] = os.path.join(sample_dir,"run_%s" % sample)

            # Move all files from temporary local dir to permanent base_dir
            self.local_finish(use_dir,sample_dir)       # Sees to copying local files to final destination (and other stuff)

            self.create_low_level_script()
