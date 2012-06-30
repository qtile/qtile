#!/bin/sh

rm -rf _build/*

while [ true ]; do
    make html
    sleep 5
done
