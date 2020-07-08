#!/bin/sh

# This script uses Homebrew to install the contents of Brewfile to an EFS filesystem,
# so that the libraries can be used by Lambda.  If the filesystem is not mounted,
# this script will install the mount driver using yum and then mount it.
#
# This script is designed to be used on an Amazon EC2 instance, but should work
# on any machine with access to the EFS and with yum installed.
#
# Usage: brew_install_efs.sh [efs_filesystem_id]

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [efs_filesystem_id]"
    exit 1
fi

EFS_ID=$1
MOUNT_PATH=/mnt/efs
REGION="eu-west-1"

# If EFS has not yet been mounted, mount it

if ! mount | grep -q "$EFS_ID"; then
    echo "Mounting EFS $EFS_ID into ${MOUNT_PATH}...";
    yum install -y amazon-efs-utils;
    sed -i "s/\#region = us-east-1/region = ${REGION}/" /etc/amazon/efs/efs-utils.conf
    
    mkdir -p ${MOUNT_PATH};
    mount -t efs $EFS_ID:/ ${MOUNT_PATH};

    if [ ! $? -eq 0 ]; then
        echo "Failed to mount EFS"
        exit 1
    fi

    mkdir -p ${MOUNT_PATH}/lambda_packages;
    echo "Mounted successfully.";
fi

./brew_install.sh ${MOUNT_PATH}/lambda_packages;
