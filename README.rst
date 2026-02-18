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

.. note::

   The ``main`` branch is unstable (trunk-based development). Use a specific tagged
   version for production use.

On Stretch 3, install and run directly with ``uvx``.

Recommended — specific version (e.g., ``v0.0.2``):

.. code-block:: bash

    set -a; source .env; set +a  # Only needed if using TTS/ASR
    uvx --python 3.12 --from "git+https://github.com/lnfu/stretch3-zmq.git@v0.0.2" stretch3-zmq-driver

Latest (unstable main branch):

.. code-block:: bash

    set -a; source .env; set +a  # Only needed if using TTS/ASR
    uvx --python 3.12 --from https://github.com/lnfu/stretch3-zmq.git stretch3-zmq-driver
