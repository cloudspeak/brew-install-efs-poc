# Homebrew EFS installer for Lambda libraries Proof-of-Concept

This is a proof-of-concept workflow for deploying Lambda functions which rely on Homebrew-packaged libraries,
stored on an EFS filesystem.  The project is arranged as
follows:

* The Lambda source is contained in the `src` folder.  It contains a simple placeholder function which uses `libproj`.
* The Lambda's dependencies are given in `Brewfile`.  It currently just contains the `proj` formula.
* The infrastructure for creating the Lambda, EFS filesystem and VPC is in the Pulumi program `__main__.py`.
* The script to install Homebrew dependencies into the EFS filesystem is contained in `brew_install_efs.sh`.
    It is designed to be executed on an EC2 instance.

## Usage

1. First, **clone the repo set up your local development environment** in the usual way:

```
git clone https://github.com/cloudspeak/brew-install-efs-poc
cd brew-install-efs-poc/
virtualenv -p /usr/bin/python3 venv
source ./venv/bin/activate
pip install -r requirements.txt
```

2. **Deploy the infrastructure** with Pulumi:

```
pulumi up
```

This will create the Lambda, VPC and filesystem, but the Lambda will not work yet because the dependencies aren't installed.
Make a note of the outputs given by Pulumi.

3. **Create a Cloud9 instance** via the AWS console, ensuring you put it in the VPC created by Pulumi
above.  Then, in the EC2 console, **add your newly created Cloud9 instance to the security group**
created by Pulumi.  This manual step is required because Cloud9 does have an option for choosing the security group upon creation.

4. **Run the same commands as Step 1 in Cloud9** to checkout the repo and (optionally) set up a development environment.

5. **Run the following command to install the contents of the `Brewfile` to EFS**, where
   `[ef-filesystem-id]` is the EFS filesystem ID given in the Pulumi outputs:

```
./brew_install_efs.sh [ef-filesystem-id]
```

6. **The Lambda will now be able to access its dependencies.**  To continue development, simply
   repackage (using [`lambda_package`](https://github.com/nuage-studio/lambda-package)) and deploy the Lambda as usual, and if it requires additional dependencies,
   add them to the Brewfile and re-run the script on Cloud9/EC2.

## Known issues and limitations

* The manual step for creating Cloud9 instances in a security group is problematic.  It could be
  resolved by creating Cloud9 instances programatically, although it will require a manual API
  call since the Pulumi resource also has no security group option.

* Sometimes the EC2 instance runs out of storage space when installing dependencies via Docker.
  Possibly some more advanced setup (e.g. storing the entire Cellar on EFS temporarily) will be
  necessary.

* The Lambda has to have its `PATH` and `LD_LIBRARY_PATH` environment variables updated to include
  the EFS library location, but there is no sensible way of appending to their existing values given
  by the AWS environment.  As a result, the Pulumi program has to know what these existing values
  usually are in order to set them, and if AWS change anything that won't be reflected in these
  Lambdas.
