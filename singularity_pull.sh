#/bin/bash

# This script pulls a pre-built singularity container image from the library.
# If this is run on MacOS, then it spins up a Vagrant virtual machine running
# Ubuntu (because singularity only runs on Linux).


if [ "$(uname)" == "Darwin" ]; then
    printf "\nDetected MacOS."
    # Do something under Mac OS X platform

    # Spin up a Vagrant VM.
    vagrant up && \
    # Pull the latest container from the singularity library into the
    # singularity container.
    vagrant ssh -c '/bin/bash singularity pull singularity.sif library://laelbarlow/default/amoebae:latest' && \
    # Move the .sif file into the directory synced with the host. This will
    # overwrite any existing file with the same name in that directory.
    vagrant ssh -c 'mv singularity.sif amoebae/singularity.sif' && \
    # Shut down VM.
    vagrant halt
    # Erase VM.
    #vagrant destroy

elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    printf "\nDetected Linux."
    # Do something under GNU/Linux platform

    # Pull the latest container from the singularity library.
    singularity pull singularity.sif library://laelbarlow/default/amoebae:latest

elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW32_NT" ]; then
    printf "\nDetected Windows."
    # Do something under 32 bits Windows NT platform
    echo "AMOEBAE has not been tested on Windows, please contact the developer."
    exit 1

elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW64_NT" ]; then
    printf "\nDetected Windows."
    # Do something under 64 bits Windows NT platform
    echo "AMOEBAE has not been tested on Windows, please contact the developer."
    exit 1
fi
