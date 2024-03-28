#!/bin/bash

rsync -avz --delete --exclude target/ --exclude .git/ --exclude .github/ --exclude .gitignore  . $1
