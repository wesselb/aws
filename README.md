# [AWS](http://github.com/wesselb/aws)

[![CI](https://github.com/wesselb/aws/workflows/CI/badge.svg?branch=master)](https://github.com/wesselb/aws/actions?query=workflow%3ACI)
[![Coverage Status](https://coveralls.io/repos/github/wesselb/aws/badge.svg?branch=master&service=github)](https://coveralls.io/github/wesselb/aws?branch=master)
[![Latest Docs](https://img.shields.io/badge/docs-latest-blue.svg)](https://wesselb.github.io/aws)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Manage AWS EC2 instances for experiments

## Local Installation of Repository

See [the instructions here](https://gist.github.com/wesselb/4b44bf87f3789425f96e26c4308d0adc).
Then clone and enter the repo.

```bash
git clone https://github.com/wesselb/aws
cd aws
```

Finally, make a virtual environment and install the requirements.

```bash
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt -e .
```

## Sample Experiment

In the following, values that you need to set are bash variables (like `$REPO`) or
Python constants (like `KEY`).

### Setup AWS

* Install and configure the Amazon CLI.

* Create a new EC2 instance with the Deep Learning Base AMI (Amazon Linux 2).

* Create and name a new security group.

* Edit the new security group to allow incoming NFS within the security group.

* Create an EFS. Correctly configure the security groups for the access points.

### Create an Image

* Create a key for GitHub.

```bash
ssh-keygen -f ~/.ssh/github -t ed25519 -C "email@host.com" \
    && (echo "Host github.com"                 > ~/.ssh/config) \
    && (echo "    IdentityFile ~/.ssh/github" >> ~/.ssh/config) \
    && chmod 644 ~/.ssh/config \
    && echo "Public key:" \
    && cat ~/.ssh/github.pub
```

* Add the public key to your GitHub account.
   
* Configure the instance:

```bash
sudo amazon-linux-extras install python3.8 \
    && sudo yum install -y tmux htop python38-devel \
    && sudo pip3.8 install --upgrade pip setuptools Cython numpy virtualenv
```

* Setup the AWS repository:

```bash
cd ~
git clone git@github.com:wesselb/aws.git \
    && cd aws \
    && virtualenv venv -p python3.8 \
    && source venv/bin/activate \
    && pip install -r requirements.txt -e . \
    && deactivate \
    && cd ..
```

* Setup the project repository:

```bash
cd ~
git clone git@github.com:$USER/$REPO.git \
    && cd $REPO \
    && virtualenv venv -p python3.8 \
    && source venv/bin/activate \
    && pip install torch==1.8.1+cu111 torchvision==0.9.1+cu111 torchaudio==0.8.1 -f https://download.pytorch.org/whl/torch_stable.html \
    && pip install -r requirements.txt -e . \
    && deactivate \
    && cd ..
```

* If necessary, transfer data to the instance:

```bash
rsync -e "ssh -i ~/.ssh/$KEY.pem" -Pav $DATA_DIR ec2-user@$IP:/home/ec2-user/$REPO
```

* Stop the instance and create an image.

* Once the image is ready, terminate the instance.

### Test the Cluster

* Create a file `cluster.py`:

```python
import aws.experiment as experiment
import aws.monitor as monitor

experiment.config["ssh_user"] = "ec2-user"
experiment.config["ssh_pem"] = f"~/.ssh/{KEY}.pem"
experiment.config["setup_commands"] = [
    "cd /home/ec2-user",
    "mkdir -p efs",
    "mountpoint -q efs || sudo mount ...",  # Insert the right mounting command for the EFS.
    "sudo chmod 777 efs",
    "cd /home/ec2-user/pac-bayes-nps",
    "ssh-keygen -F github.com || ssh-keyscan github.com >>~/.ssh/known_hosts",
    "git pull"
]

commands = [
    "mkdir -p ../efs/output && touch ../efs/output/one.txt",
    "mkdir -p ../efs/output && touch ../efs/output/two.txt",
    "mkdir -p ../efs/output && touch ../efs/output/three.txt",
]

experiment.manage_cluster(
    commands,
    instance_type="t2.small",
    key_name=KEY,
    security_group_id=SECURITY_GROUP,
    image_id=IMAGE_ID,
    sync_sources=["/home/ec2-user/efs/output"],
    sync_target="sync",
    monitor_call=monitor.shutdown_after_a_while_call(duration=5 * 60),
    monitor_delay=60,
    monitor_aws_repo="/home/ec2-user/aws",
)
```

* Here's what it can do:

```bash
usage: cluster.py [-h] [--sync-stopped] [--spawn SPAWN] [--kill] [--stop]
                  [--terminate] [--start]

optional arguments:
  -h, --help      show this help message and exit
  --sync-stopped  Synchronise all stopped instances.
  --spawn SPAWN   Spawn instances.
  --kill          Kill all running experiments.
  --stop          Stop all running instances
  --terminate     Terminate all instances.
  --start         Start all experiments.
  ```

* Make an empty directory to synchronise to:

```bash
mkdir sync
```

* Test that no instances are running:

```bash
$ python cluster.py
Instances still running: 0
Sleeping for two minutes...
```

* Kill the script. Now spawn two instances and start the experiment:

```bash
$ python cluster.py --spawn 2 --start
...
```

* Check that `sync` contains the three files.

*
    Login into one of the instances to check that `/home/ec2-user/efs` also contains the
    three files.
    
* Now wait ten minutes. Eventually no instance should still be running.

*
    Kill the script.
    Now that all instances are stopped, remove everything in `sync` and attempt to sync
    the stopped instances:
    
```bash
$ python cluster.py --sync-stopped
```

* If that succeeded, then we're golden! Terminate all instances of the cluster.

```bash
$ python cluster.py --terminate
Terminating all instances:
Instances still running: 0
Sleeping for two minutes...
```

Kill the script.
You're now good to run your big experiment!


