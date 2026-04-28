# Public Transport Demand and Network Planning and Operations (CIEQ6232) - TU Delft

For any questions regarding this software contact Rajat Verma (R.Verma@tudelft.nl) or Tao Peng (T.Peng-2@tudelft.nl)

----

## Installation
We provide two alternative options to run this software: you can locally install the software in your personal machine or you can use a Virtual Machine (VM) with Ubuntu and the dependencies already set up.

**Please note that if you are using the students' computer labs @ TU Delft you must use the VM, since you don't have admin privileges to install the dependencies locally on those machines**

### Local installation
If you want to run the code locally in your computer, you need to follow these instructions.

1. Install the `conda` package manager via either [Anaconda](https://www.anaconda.com/download) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
2. Install build dependencies for Linux/Windows:
    - **For Windows users**. Download the latest Microsoft Visual C++ Build Tools: 
       * You can download the Community Edition from [visualstudio.microsoft.com/downloads](https://visualstudio.microsoft.com/downloads).
       * In the installation wizard, check the "Desktop development with C++" workload to install the C++ development environment. 
    - **For Linux users**. You need GCC compiler (in Ubuntu, install it with `sudo apt install build-essential`)
3. Create the conda environment that installs all the necessary dependencies.
   - Open conda in a terminal (on Linux and macOS; for Windows, open Anaconda Prompt).
   - Move into the directory where this README file is located.
       * Linux/macOS: use the command `cd` in the terminal (e.g., `cd /home/user/repo-main`)
       * Windows: use `cd` to move to the target directory. For example, `cd C:\Users\user\Documents\repo-main`. If you have many disk partitions, you need to first move to the partition where the file is located, for example, 'D:' and then `cd D:\Documents\repo-main`.
   - Run the following command: `conda env create -f environment.yml`. Make sure the `environment.yml` file is located in the same folder as in the terminal.
   - Follow the instructions in the terminal for conda environment creation. Press `y` and hit Enter/Return when the terminal prompts for package installation confirmation.
   - If the process runs properly, the conda environment with all the essential packages and dependencies will have been installed.
   
4. Run the Jupyter notebook
   - Activate the newly created environment with `conda activate pt-networks`.
   - Start a new Jupyter instance using `jupyter notebook`.
        - If you wish to use any other Jupyter-capable editor like Pycharm or VS Code, open the Jupyter editor using their instructions.
   - A new window will open in your web browser. Select the file `notebook.ipynb` from the list and start working on your assignment :)

### Using a VM

#### In the students' computer labs @ TU Delft

1. Run **Haskell VM Import CIEQ6232** from the start menu to load the VM image. Press any key when the script finishes to exit.
2. Run **Oracle VM VirtualBox** from the start menu, select the machine cieq6232 and go to the Settings->USB and select the option USB 1.1 (if not already selected)
3. Run the VM with the green start button.
4. The login details for Ubuntu in the VM are:
    - user: cieq6232
    - pass: cieq6232
5. Within the VM, open a terminal from the left side panel. In the terminal, move to the directory with the code `cd ~/Documents/repo-main`, and follow step 4 in the local installation instructions to run the code. 

Note: you may want to adjust the screen resolution to fit the screen better. For this, you can right click in the desktop and select Display Settings.   

#### Running the VM in your own device

1. Install [Virtual Box](https://www.virtualbox.org/)
2. Download the VM from [here](https://surfdrive.surf.nl/s/QtBC56Bwykoepjc).
3. Import the VM to Virtual Box and Start it (more info [here](https://docs.oracle.com/cd/E26217_01/E26796/html/qs-import-vm.html))
4. The login details for Ubuntu in the VM are:
    - user: cieq6232
    - pass: cieq6232
5. Within the VM, open a terminal from the left side panel. In the terminal, move to the directory with the code `cd ~/Documents/repo-main`, and follow step 4 in the local installation instructions to run the code.    

Note: you may want to adjust the screen resolution to fit the screen better. For this, you can right click in the desktop and select Display Settings.   

<!-- ----

## Using the code

You can find a video tutorial on how to use this tool [here](https://surfdrive.surf.nl/files/index.php/s/Td4xD7GIDDefniP) -->
