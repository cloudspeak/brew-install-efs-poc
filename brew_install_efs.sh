#!/bin/sh

# This script uses Homebrew to install the contents of Brewfile to an EFS filesystem,
# so that the libraries can be used by Lambda.

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [efs_filesystem_id]"
    exit 1
fi

EFS_ID=$1


# If EFS has not yet been mounted, mount it

if ! mount | grep -q "$EFS_ID"; then
    echo "Mounting EFS $EFS_ID into ./efs..."
    sudo yum install -y amazon-efs-utils;
    sudo mkdir -p efs;
    sudo mount -t efs $EFS_ID:/ efs;
    sudo mkdir efs/lambda_packages;
fi

# Docker script which:
#  1. Installs dependencies with brew
#  2. Copies them to the EFS lambda_packages/lib folder
#  3. Ensures that objdump and ld are present

# SCRIPT="

# if [ ! -f input/Brewfile ]; then
#   echo 'ERROR: Cannot find Brewfile in local directory';
# fi;

# echo 'Invoking brew...'
# cp input/Brewfile .;
# brew bundle install;

# echo 'Copying libraries to lambda_packages/lib...';
# mkdir -p /lambda_packages/bin;
# mkdir -p /lambda_packages/lib;
# cp .linuxbrew/lib/*.so /lambda_packages/lib;

# if [ ! -f /lambda_packages/bin/ld || -f /lambda_packages/bin/objdump ]; then
#     echo 'Installing objdump and ld...'
#     yum install -y yum-utils rpmdevtools;
#     yumdownloader --resolve binutils;
#     rpmdev-extract *.rpm;
#     cp -P -R /tmp/binutils*/usr/lib64/* /lambda_packages/lib;
#     cp -P /tmp/binutils*/usr/bin/ld.bfd /lambda_packages/bin/ld;
#     cp -P /tmp/binutils*/usr/bin/objdump /lambda_packages/bin;
# "

# # Run docker to install contents of brewfile
# docker run -v $(pwd):inputdir $(pwd)/efs/lambda_packages:lambda_packages nuagestudio/amazonlinuxbrew bash -c "${SCRIPT}"
