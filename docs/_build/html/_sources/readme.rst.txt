`AWS <http://github.com/wesselb/aws>`__
=======================================

|Build| |Coverage Status| |Latest Docs|

Manage AWS EC2 instances for experiments

Installation
------------

See `the instructions
here <https://gist.github.com/wesselb/4b44bf87f3789425f96e26c4308d0adc>`__.
Then clone and enter the repo.

.. code:: bash

    git clone https://github.com/wesselb/aws
    cd aws

Finally, make a virtual environment and install the requirements.

.. code:: bash

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements.txt

.. |Build| image:: https://travis-ci.org/wesselb/aws.svg?branch=master
   :target: https://travis-ci.org/wesselb/aws
.. |Coverage Status| image:: https://coveralls.io/repos/github/wesselb/aws/badge.svg?branch=master&service=github
   :target: https://coveralls.io/github/wesselb/aws?branch=master
.. |Latest Docs| image:: https://img.shields.io/badge/docs-latest-blue.svg
   :target: https://wesselb.github.io/aws
