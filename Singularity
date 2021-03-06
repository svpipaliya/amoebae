# Singularity container image recipe.

# Copyright 2018 Lael D. Barlow
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 

# This file defines how to generate a Singularity container in which to run
# AMOEBAE.

# Base the singularity image on a singularity container debian, version 9,
# distribution of linux provided online. Note: This is reproducible.
Bootstrap: library
From: debian:sha256.85e28e6a4e8934e427ab050f8d895a94029e8cf471d6e0bc9d8a9735f0a0c3a4

###################################
###################################
# This section installs anaconda similarly to a Dockerfile provided online: 
# https://hub.docker.com/r/continuumio/anaconda3/dockerfile

%environment
#export LANG=C.UTF-8
#export LC_ALL=C.UTF-8
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"
# Try to update the locale so snakemake works (the /etc/default/locale file is
# empty)...
echo -e 'LANG=en_US.UTF-8\nLC_ALL=en_US.UTF-8' > /etc/default/locale # Doesn't seem to work...
export PATH=/opt/conda/bin:$PATH

%post
    apt-get update --fix-missing && apt-get install -y wget curl bzip2 ca-certificates \
    libglib2.0-0 libxext6 libsm6 libxrender1 \
    git mercurial subversion

    # Install miniconda
    cd /opt
    curl -o /opt/miniconda.sh -O \
    https://repo.anaconda.com/miniconda/Miniconda3-4.7.12.1-Linux-x86_64.sh &&\
    chmod +x /opt/miniconda.sh
    /opt/miniconda.sh -b -p /opt/conda
    rm /opt/miniconda.sh

    echo 'export PATH=/opt/conda/bin:$PATH' >>$SINGULARITY_ENVIRONMENT
    export PATH=/opt/conda/bin:$PATH

    ## Install Tini for reaping zombie processes.
    #apt-get install -y curl grep sed dpkg && \
    #TINI_VERSION=`curl https://github.com/krallin/tini/releases/latest | grep -o "/v.*\"" | sed 's:^..\(.*\).$:\1:'` && \
    #curl -L "https://github.com/krallin/tini/releases/download/v${TINI_VERSION}/tini_${TINI_VERSION}.deb" > tini.deb && \
    #dpkg -i tini.deb && \
    #rm tini.deb && \
    #apt-get clean

###################################
###################################
# Install AMOEBAE dependencies.

# These packages are necessary for installing ete3:
# ete3 3.1.1 does not work with Python 3.7 or above.
conda install -y python=3.6.9
# libgl1-mesa-dev is a dependency of PyQt, which is apparently not provided via
# conda.
apt-get install -y libgl1-mesa-dev
# PyQt5 is necessary for ete3 to generate graphics.
conda install -y pyqt
# Check that PyQt5 can actually be imported via python3.
python3 -c "from PyQt5 import QtGui"

# Install ete3 (the ete3 external tools are not available for install via conda
# on linux).
conda install -y -c etetoolkit ete3 ete_toolchain
# Check that ete3 was installed correctly.
ete3 build check
# This raises a missing external tool "slr".



# This fails:
#RUN conda install -c anaconda gcc

# Install a C compiler.
#RUN apt install build-essential

# Install GCC for compiling mrbayes.
#RUN conda install -c anaconda gcc # Didn't work because of missing dependancy.
# Install clang instead for compiling mrbayes.
#RUN conda install -c anaconda clang # Also doesn't work!

# Install MrBayes for phylogenetic analysis.
#RUN conda install -c bioconda mrbayes
#RUN echo '***********************************' && \
#    echo '*******        MrBayes        *****' && \
#    echo '***********************************' && \
#    git clone --depth=1 https://github.com/NBISweden/MrBayes.git  --branch v3.2.7a &&\
#    cd MrBayes &&\
#    ./configure &&\
#    make && sudo make install
#
#WORKDIR /home/amoebae_user/software




# Install biopython for parsing various bioinformatics software output files,
# etc.
conda install -y -c anaconda biopython

# Install NCBI BLAST for similarity searching.
#RUN conda install -c bioconda blast
echo '***********************************' && \
echo '*******Installing ncbi-blast+ *****' && \
echo '***********************************' && \
#wget "ftp://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/ncbi-blast-2.10.0+-x64-linux.tar.gz" &&\
#tar zxvpf ncbi-blast-2.10.0+-x64-linux.tar.gz && \
#rm ncbi-blast-2.10.0+-x64-linux.tar.gz
wget "ftp://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/2.9.0/ncbi-blast-2.9.0+-x64-linux.tar.gz" &&\
tar zxvpf ncbi-blast-2.9.0+-x64-linux.tar.gz && \
rm ncbi-blast-2.9.0+-x64-linux.tar.gz

# Install HMMer3 for similarity searching.
conda install -y -c bioconda hmmer

# Install iqtree for phylogenetic analysis.
echo '***********************************' && \
echo '*******  Installing IQ-TREE   *****' && \
echo '***********************************' && \
wget "https://github.com/Cibiv/IQ-TREE/releases/download/v1.6.12/iqtree-1.6.12-Linux.tar.gz" && \
tar zxvpf iqtree-1.6.12-Linux.tar.gz &&\
rm iqtree-1.6.12-Linux.tar.gz

# Install MUSCLE for multiple sequence alignment.
echo '***********************************' && \
echo '*******  Installing MUSCLE    *****' && \
echo '***********************************' && \
wget "https://www.drive5.com/muscle/downloads3.8.31/muscle3.8.31_i86linux64.tar.gz" && \
tar zxvpf muscle3.8.31_i86linux64.tar.gz && \
rm muscle3.8.31_i86linux64.tar.gz && \
mv muscle3.8.31_i86linux64 muscle

# Install additional python packages.
# *** This will update the most recent versions of these packages, which may be
# a reproducibility issue.
#apt-get -y install python3-pip
pip install --upgrade pip
pip install gffutils
pip install PyPDF2
pip install reportlab

# Install exonerate for exon prediction (at least better than TBLASTN).
#RUN echo '***********************************' && \
#    echo '******* Installing exonerate  *****' && \
#    echo '***********************************' && \
#    wget "http://ftp.ebi.ac.uk/pub/software/vertebrategenomics/exonerate/exonerate-2.2.0-x86_64.tar.gz" &&\
#    tar zxvpf exonerate-2.2.0-x86_64.tar.gz && \
#    rm exonerate-2.2.0-x86_64.tar.gz
#
#ENV PATH "$PATH:/home/amoebae_user/software/exonerate-2.2.0-x86_64/bin"
# Install via conda.
conda install -y -c bioconda exonerate

# Install jupyter.
conda install jupyter

# Install and enable relevant jupyter notebook extensions.
# This includes the TableOfContents (toc2) extension for navigating large jupyter
# notebooks: https://jupyter-contrib-nbextensions.readthedocs.io/en/latest/nbextensions/toc2/README.html
# documentation: https://github.com/ipython-contrib/jupyter_contrib_nbextensions
conda install -y -c conda-forge jupyter_contrib_nbextensions
jupyter contrib nbextension install --user
jupyter nbextension enable toc2/main
#jupyter nbextension enable spellchecker/main

# Install latex.
#apt-get install -y texlive-xetex texlive-fonts-recommended texlive-generic-recommended
apt-get install -y texlive-xetex texlive-fonts-recommended texlive-generic-extra
apt-get install -y texlive-bibtex-extra
apt-get install -y pandoc

# Install program for displaying directory contents in a tree structure.
apt-get install tree

# Install python package for parsing bibtex files.
pip install bibtexparser

# Upgrade jupyter.
#conda update jupyter

# Install pandas for working with spreadsheets, etc.
conda install pandas

# Install matplotlib for plotting.
conda install -c conda-forge matplotlib

## Install snakemake in an environment called "snakemake".
## To activate the snakemake environment, type "conda activate snakemake".
#conda install -c conda-forge mamba
#mamba create -c conda-forge -c bioconda -n snakemake snakemake

# Install snakemake.
conda install -c bioconda snakemake

# Install graphics package for visualizing snakemake pipelines.
apt-get install -y graphviz

# Install python packages for making https requests.
conda install -c anaconda certifi
conda install -c anaconda requests

## Install entrezpy for downloading sequences from NCBI.
#conda install -c bioconda entrezpy # Does not work as advertised.

# Install Vim for text editing.
apt-get install -y vim

# install PyTest.
pip install -U pytest

# Make an internal clone of the amoebae github code repository so that the
# singularity container can be used as a stand-alone component of a pipeline.
cd /opt
git clone https://github.com/laelbarlow/amoebae.git --depth 1 --single-branch --branch master
mv amoebae internal_amoebae
cd internal_amoebae
cp settings.py.example settings.py
chmod a+x amoebae
chmod a+x misc_scripts/*.py
cd /opt



%environment
export PATH="$PATH:/opt/conda/bin"
export PATH="$PATH:/opt/ncbi-blast-2.9.0+/bin"
export PATH="$PATH:/opt/iqtree-1.6.12-Linux/bin"
export PATH="$PATH:/opt/"
export PATH="$PATH:/opt/amoebae"
export FONTCONFIG_PATH=/etc/fonts
