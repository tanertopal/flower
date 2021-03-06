# Fashion-MNIST Benchmarks

## Prepare

To execute the `run.py` script you need to create a `.flower_ops` file in the
git root of this project. The file needs to contain the following fields:

```
[paths]
wheel_dir = ~/development/adap/flower/dist/
wheel_filename = flower-0.0.1-py3-none-any.whl

[aws]
image_id = ami-0396b4e13e2f040cc
key_name = AWS_KEY_NAME
subnet_id = YOUR_AWS_SUBNET_ID
security_group_ids = YOUR_AWS_SECURITY_GROUP_ID
logserver_s3_bucket = YOUR_S3_BUCKET

[ssh]
private_key = PATH_TO_YOU_PRIVATE_KEY_TO_SSH_INTO_THE_MACHINES
```

### Remarks

#### Wheel directory

Adjust the wheel directory according to the localation of the repo on your
machine.

#### Security Group

The security group needs to have port 8080 open so that the clients can connect
to the server.

#### Subnet Id

We are starting all instances in the same subnet to be more cost efficent
(traffic between EC2 instances in the same subnet over their private IP does
not incure any cost).

#### AMI

The provided AMI is a bare Ubuntu 18.04 image which was modified using the
`dev/aws_ami_bootstrap.sh` script.

## Build Docker Container

```bash
./docker/build.sh
```

## Build Python Wheel

To execute the latest version of your benchmarks during development, please 
ensure that the `.whl` build in `dist/` reflects your changes. Re-build
if necessary:

```bash
./dev/build.sh
```

## Execute

To execute a benchmark setting locally using docker:

```bash
python -m flower_benchmark.tf_fashion_mnist.run --adapter="docker" --setting="minimal"
```

To execute a benchmark setting remotely on AWS:

```bash
python -m flower_benchmark.tf_fashion_mnist.run --adapter="ec2" --setting="minimal"
```
