stretch3-zmq
============
A simple ZeroMQ-based driver for the
`Hello Robot Stretch 3 <https://hello-robot.com/stretch-3-product>`_.

Packages
--------
This monorepo contains two installable packages that share the ``stretch3_zmq`` namespace:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Package
     - Import root
     - Purpose
   * - ``stretch3-zmq-core``
     - ``stretch3_zmq.core``
     - Shared message schemas (Pydantic + msgpack). Lightweight — no robot hardware deps.
   * - ``stretch3-zmq-driver``
     - ``stretch3_zmq.driver``
     - Full robot driver: ZeroMQ services, TTS/ASR, camera support, robot control.

Setup
-----
**Optional:** For TTS/ASR functionality, create a `.env` file with your API keys:

.. code-block:: bash

    cp .env.example .env
    # Edit .env and add your API keys

Run (Driver)
------------
.. note::
   The ``main`` branch is unstable (trunk-based development). Use a specific tagged
   version for production use.

On Stretch 3, install and run directly with ``uvx``.

Recommended — specific version (e.g., ``v0.0.3``):

.. code-block:: bash

    set -a; source .env; set +a  # Only needed if using TTS/ASR
    uvx --python 3.12 --from "stretch3-zmq-driver @ git+https://github.com/lnfu/stretch3-zmq.git@v0.0.3#subdirectory=packages/driver" stretch3-zmq-driver

Latest (unstable main branch):

.. code-block:: bash

    set -a; source .env; set +a  # Only needed if using TTS/ASR
    uvx --python 3.12 --from "stretch3-zmq-driver @ git+https://github.com/lnfu/stretch3-zmq.git#subdirectory=packages/driver" stretch3-zmq-driver

Install (Core Library)
----------------------
If you only need the message schemas (e.g., for a remote client), install ``stretch3-zmq-core``
without the heavy driver dependencies.

Using ``uv``:

.. code-block:: bash

    uv add "stretch3-zmq-core @ git+https://github.com/lnfu/stretch3-zmq.git#subdirectory=packages/core"

Using ``pip``:

.. code-block:: bash

    pip install "git+https://github.com/lnfu/stretch3-zmq.git#subdirectory=packages/core"

Specific version (e.g., ``v0.0.3``):

.. code-block:: bash

    pip install "git+https://github.com/lnfu/stretch3-zmq.git@v0.0.3#subdirectory=packages/core"

Then import from ``stretch3_zmq.core``:

.. code-block:: python

    from stretch3_zmq.core.messages.command import ManipulatorCommand
    from stretch3_zmq.core.messages.status import Status
    from stretch3_zmq.core.messages.protocol import decode_with_timestamp
