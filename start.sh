#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Print help if requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: ./start.sh [options]"
    echo "Options are passed directly to the python script."
    python3 main.py --help
    exit 0
fi

# Run the python script with all arguments passed to this shell script
python3 main.py "$@"
