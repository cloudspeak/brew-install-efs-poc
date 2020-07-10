# Homebrew EFS installer for Lambda libraries Proof-of-Concept

This is a proof-of-concept workflow for deploying Lambda functions which rely
on Homebrew-packaged libraries, stored on an EFS filesystem.  The project is
arranged as follows:

* The Lambda source is contained in the `src` folder.  It contains a simple placeholder function which uses `libproj`.
* The Lambda's dependencies are given in `Brewfile`.  It currently just contains the `proj` formula.
* The infrastructure for creating the Lambda, EFS filesystem and VPC is defined in the Pulumi program `__main__.py` and in the `pulumi_infrastructure` folder.

> **Note:** Deploying this stack will incur monthly charges due to the
> presence of a NAT Gateway.

## Usage

To deploy the project, simple **clone the repo set up your local development environment** in the usual way:

```
git clone https://github.com/cloudspeak/brew-install-efs-poc
cd brew-install-efs-poc/
virtualenv -p /usr/bin/python3 venv
source ./venv/bin/activate
pip install -r requirements.txt
```

And then **deploy the infrastructure** with Pulumi:

```
pulumi up
```

Make a note of the outputs given by Pulumi, as they will be needed later.

This will create the Lambda, VPC, CodeBuild project and filesystem, but the Lambda will not work yet because the dependencies aren't installed.
You can install them manually on a Cloud9 instance, or you can trigger a CodeBuild build.  See the instructions below for each.

## Install dependencies using Cloud9

You can use a Cloud9 interactive shell to develop the project and install the
Lambda's dependencies by following these steps:

1. **Create a Cloud9 instance** via the AWS console, ensuring you put it in the VPC created by Pulumi
above, and that you choose one of the **public** subnets output by Pulumi.  Then, in the EC2 console,
**add your newly created Cloud9 instance to the security group**
created by Pulumi.  This manual step is required because Cloud9 does have an option for choosing the security group upon creation.

2. **Run the same commands as the Usage section above in Cloud9** to checkout the repo and (optionally) set up a development environment.

3. **Run the following command to install the contents of the `Brewfile` to EFS**, where
   `[ef-filesystem-id]` is the EFS filesystem ID given in the Pulumi outputs:

```
./brew_install_efs.sh [ef-filesystem-id]
```

4. **The Lambda will now be able to access its dependencies.**  To continue development, simply
   repackage (using [`lambda_package`](https://github.com/nuage-studio/lambda-package)) and deploy the Lambda as usual, and if it requires additional dependencies,
   add them to the Brewfile and re-run the script on Cloud9/EC2.

## Install dependencies using CodeBuild

After you have deployed the stack the first time, a CodeBuild project will be set up to install your Lambda's dependencies and deploy the stack.  First however, you must allow CodeBuild access to your Pulumi account.

1. **[Create a Pulumi access token](https://app.pulumi.com/cloudspeak/settings/tokens)**.

2. On the AWS console, **open the Parameter Store** in the Systems Manager section.  You will see a parameter created by Pulumi (if you have more than one stack, check the Pulumi output to see the name of the parameter it created).  **Set the parameter value to your access token**.

3. Go to the CodeBuild console to trigger a build.

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


* Currently, when libraries are copied from Homebrew's prefix to the EFS location, all symlinks
  are resolved into actual files meaning the resulting `lib` folder is larger than necessary.  This could be resolved in the future with a more clever readjustment of symlinks.

* In order for CodeBuild to work inside a VPC, it requires a NAT instance, which incurs a charge (around $25
  per month at the time of writing).

* CodeBuild has support for EFS, but this is not yet supported by Terraform/Pulumi, so is currently performed manually in the buildspec.yml.

* Currently CodeBuild is very slow because it installs Pulumi, the EFS driver and a Homebrew image every time it runs.  This can be fixed by creating a custom docker image.

* Currently Homebrew does not see which packages are already installed so reinstalls them every time.  This can be fixed.

* **Beware that as a proof of concept, the CodeBuild service role is currently given full admin privileges**.  This should not be used in production environments.
