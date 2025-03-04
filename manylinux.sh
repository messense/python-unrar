#!/bin/bash
cd dependencies/unrar
make lib
cd ../..

cp dependencies/unrar/libunrar.so /io/unrar/libunrar.so

# Build wheels
which linux32 && LINUX32=linux32
$LINUX32 /opt/python/cp27-cp27mu/bin/python setup.py bdist_wheel

# Audit wheels
for wheel in dist/*-linux_*.whl; do
  auditwheel repair $wheel -w dist/
  rm $wheel
done
