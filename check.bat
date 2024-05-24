@echo off
cd src
mypy . --explicit-package-bases
cd ..
@echo on
