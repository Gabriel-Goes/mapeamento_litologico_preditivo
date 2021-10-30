#                                                  THIS IS THE DELEVOPMENT BRANCH

# ------------------------------------------------------- !ATENTION! --------------------------------------------------------------- #

# IF YOU SEEK FOR THE BASICS OF PYTHON PROGRAMMING LANGUAGES FOR GEOSPATIAL DATA ANALYSIS *HEAD TO TUTORIAL BRANCHES BY TYPING:

	git branch Tutorials

# ------------------------------------------------------- !ATENTION! --------------------------------------------------------------- #

# This file contains a Summary list and Summanry Description

# Summary List:
-1 Machine Assembly;
	Construction of a local machine to process our data.

-2 Operational System;
	The software system that is used to interact with to hardware that we've assembled.

-3 Git (Version Control);
	Git is a tool for controlling versions enabeling group work.

-4 Programming Environment - Anaconda;
	Anaconda is a package mannager and environment builder. 
	environment.yml

-5 Programming Language
	- Python
		Tutorials 
			- Jupyter Notebooks:
  				1: GeoPandas Reading loose shp & Writing Data Base.gpkg 

# ---------------------------------------------------------------------------------------------------------------------------------- #

# Summary Description:

# The Geologist Machine Repository contain all the steps necessary to create an programming environment for geological data analysis;
	
# ----Starting from the construction of a local machine capable to execute commands through the interpretation of an logical language.

# 1 ------------------------------------------------ Machine Assembly -------------------------------------------------------------- #

# To do so, we'll need a personal computer and an operational system installed;

The local machine running this project is equiped with:

- MB: B450M DS3H;
- CPU: AMD Ryzen 3600X (6 cores, 12 threads, 3,6 to 4,4Ghz );
- RAM: 1 Module of 16Gb at 3.2Ghz & 1 Module of 8Gb at 3.2Ghz;
- GPU: Nvidia GTX 1650 Super ( 4Gb vram up to 2.1Ghz );
- DISK: 512Gb SSD ( w: 1800Mb/s; r: 3200Mb/s );


# 2 ----------------------------------------------  Operational System ------------------------------------------------------------- #

The current installed  OS is:

- Arch Linux x86_64;
- Kernel: 5.10.75-1-lts;
- shell: bash 5.1.8;
- WM: i3;

The process to install the linux distribution, kernel and Window Mannager can be found at < https://wiki.archlinux.org >


# 3 ---------------------------------------------- Git: File Versioning System ----------------------------------------------------- #

 - With git installed we can run the command:
 
	git clone git@github.com:Gabriel-Goes/mapeamento_litologico_preditivo.git

 - This command will create a directory exactly the same as it is at GitHub and we can work on the same project simuntaniously

 - Git is a powerfull and complex tool, but with a few commands we can do usefull tasks;


# 4 ----------------------------------------------  Programming Environment - Anaconda --------------------------------------------- #

 - The steps to install Anaconda can be found at < https://docs.anaconda.com/anaconda/install/linux/ >

    4.a - First step is to install the Pre-requisites packages with the following command:
    
	sudo pacman -Sy libxau libxi libxss libxtst libxcursor libxcomposite libxdamage libxfixes libxrandr libxrender mesa-libgl  alsa-lib libglvnd
  
    4.b - Second step is to download the Anaconda.sh file, a bash script that will handle the actual installation of Anaconda;
        - But before running any bash script, we have to make shure that the file is the original one and not will harm our machine, or is not corrupted. Run de command:
        
		sha256sum ~/Downloads/Anaconda3-2021.05-Linux-x86_64.sh 

#		*** Take note that the version will change, so the hash function output ***
#			*** Make sure that the version is the exact same one ***

   4.c - After downloading and verifying integrity, we can install the the package mannager with the following command: 
	bash ~/Downloads/Anaconda3-2021.05-Linux-x86_64.sh
	
   4.d - At my distribution of linux, it was necessary to send the following command to activate anaconda:
	source bin/activate root
	
   4.e - With Anaconda installed, we can build our environment runing the command:
	conda env create --file environment.yml
   
   4.f - For better practiality, we can install nb_conda_kernels. This way, we can access any environment from base env. Command:
	conda activate base
	conda install -c conda-forge nb_conda_kernels
	

# 5 ------------------------------------------------ Programming Language ----------------------------------------------------------- #

 - At this point we are fully capable of creating workflow to process and analyse our geological data;

 - We gonna start by interacting with the online database of the Brasil's Geological Service and constructing a local database inside our machine.

 - The process of this interaction and local database creation is discretized within the first Tutorial Jupyter Notebook and can be read by typing the following command:
 
	jupyter-notebook 1-Geopandas:Geopackage_as_Database.ipynb
 

