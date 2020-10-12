#!/bin/sh
echo Starting
sleep 1
echo some error message to stderr 1>&2
echo Finishing
exit 1
