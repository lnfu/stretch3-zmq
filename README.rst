stretch3-zmq
============

A simple ZeroMQ-based driver for the
`Hello Robot Stretch 3 <https://hello-robot.com/stretch-3-product>`_.

Setup
-----

**Optional:** For TTS/ASR functionality, create a `.env` file with your API keys:

.. code-block:: bash

    cp .env.example .env
    # Edit .env and add your API keys

Run
---

On Stretch 3:

.. code-block:: bash

    set -a; source .env; set +a  # Only needed if using TTS/ASR
    uvx --python 3.12 --from https://github.com/lnfu/stretch3-zmq.git stretch3-zmq-driver
