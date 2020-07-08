#!/bin/sh

# This script uses Homebrew to install the contents of Brewfile to a specified path,
# so that the libraries can be used by AWS Lambda.  It also installs ld and objdump
# to the same path, as these are necessary for Lambda functions using Python.
#
# It works by invoking a Docker instance.
#
# Usage: brew_install.sh [output_path]
#
# where `output_path` is an absolute path.

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [output_path]"
    exit 1
fi

OUTPUT_PATH=$1

# Docker script which:
#  1. Ensures that objdump and ld are present
#  2. Installs dependencies with brew
#  3. Copies them to the EFS lambda_packages/lib folder

SCRIPT="

if [ ! -f /inputdir/Brewfile ]; then
  echo 'ERROR: Cannot find Brewfile in local directory';
fi;

sudo mkdir -p /lambda_packages/bin;
sudo mkdir -p /lambda_packages/lib;

if [ ! -f /lambda_packages/bin/ld ] || [ ! -f /lambda_packages/bin/objdump ]; then
    echo 'Installing objdump and ld...';
    sudo yum install -y yum-utils rpmdevtools;
    sudo yumdownloader --resolve binutils;
    rpmdev-extract *.rpm;
    sudo cp -P -R ./binutils*/usr/lib64/* /lambda_packages/lib;
    sudo cp -P ./binutils*/usr/bin/ld.bfd /lambda_packages/bin/ld;
    sudo cp -P ./binutils*/usr/bin/objdump /lambda_packages/bin;
    sudo rm -rf ./binutils;
    sudo chmod +x /lambda_packages/bin/ld
fi

echo 'Invoking brew...'
cp /inputdir/Brewfile .;
brew bundle;


echo 'Copying libraries to lambda_packages/lib...';
sudo cp -LR /home/linuxbrew/.linuxbrew/lib/* /lambda_packages/lib;

echo 'Done.';
"

echo "Launching Docker...";

# Run docker to install contents of brewfile
docker run \
    -v $(pwd):/inputdir \
    -v ${OUTPUT_PATH}:/lambda_packages \
    nuagestudio/amazonlinuxbrew bash -c "${SCRIPT}"
