#!/bin/bash

myArray=("cat" "dog" "mouse" "frog")
for str in ${myArray[@]}; do
  echo $str
done
