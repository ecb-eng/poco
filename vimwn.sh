#!/bin/bash
echo "STARTED AT: "$(date) >> ~/.vimwn/log
export PYTHONPATH="/home/pedro/src/vimwn"
/home/pedro/src/vimwn/bin/vimwn $@ >~/.vimwn/log 2>&1
echo "ENDED AT  : "$(date) >> ~/.vimwn/log
