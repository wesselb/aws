# [AWS](http://github.com/wesselb/aws)

[![CI](https://github.com/wesselb/aws/workflows/CI/badge.svg?branch=master)](https://github.com/wesselb/aws/actions?query=workflow%3ACI)
[![Coverage Status](https://coveralls.io/repos/github/wesselb/aws/badge.svg?branch=master&service=github)](https://coveralls.io/github/wesselb/aws?branch=master)
[![Latest Docs](https://img.shields.io/badge/docs-latest-blue.svg)](https://wesselb.github.io/aws)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


Manage AWS EC2 instances for experiments

## Installation

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
pip install -r requirements.txt
```