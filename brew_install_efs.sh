#!/bin/sh

# This script uses Homebrew to install the contents of Brewfile to an EFS filesystem,
# so that the libraries can be used by Lambda.
#
# Usage: brew_install_efs.sh [efs_filesystem_id]

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [efs_filesystem_id]"
    exit 1
fi

EFS_ID=$1


# If EFS has not yet been mounted, mount it

if ! mount | grep -q "$EFS_ID"; then
    echo "Mounting EFS $EFS_ID into ./efs...";
    sudo yum install -y amazon-efs-utils;
    sudo mkdir -p efs;
    sudo mount -t efs $EFS_ID:/ efs;
    sudo mkdir -p efs/lambda_packages;
fi


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
    sudo chmod +x /lambda_packages/bin/ld
fi

echo 'Invoking brew...'
cp /inputdir/Brewfile .;
brew bundle;


echo 'Copying libraries to lambda_packages/lib...';
sudo cp -LR /home/linuxbrew/.linuxbrew/lib/* /lambda_packages/lib;

echo 'Done.';
"

# Run docker to install contents of brewfile
docker run \
    -v $(pwd):/inputdir \
    -v $(pwd)/efs/lambda_packages:/lambda_packages \
    nuagestudio/amazonlinuxbrew bash -c "${SCRIPT}"
