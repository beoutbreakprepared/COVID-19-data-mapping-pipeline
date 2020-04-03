#!/bin/bash

if which python > /dev/null 2>&1
then
  python_version=`python --version 2>&1 | awk '{print $2}'`
  echo "Python is version $python_version, starting HTTP server..."
  if [[ $python_version = 2* ]]
  then
    python -m SimpleHTTPServer 8000
  else
    # This will use port 8000 by default.
    python -m http.server
  fi
else
  echo "Please install Python first!"
fi
