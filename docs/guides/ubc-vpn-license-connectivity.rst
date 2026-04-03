UBC VPN and License Connectivity
================================

Patchworks license checks use ``SPS_LICENSE_SERVER`` in
``<user>@<server>`` form. Example placeholder:

.. code-block:: text

   <sps_user>@auth.spatial.ca

``<sps_user>`` is a template token, not a literal username.

Known-good FEMIC/Patchworks operation on UBC institutional Windows workstations
assumes Patchworks is already installed locally and the real
``SPS_LICENSE_SERVER`` value is already set in global system configuration. In
that normal Windows path, FEMIC should inherit the system environment instead
of injecting a replacement runtime value.

Primary Topology
----------------

Use host-level UBC myVPN connectivity and run FEMIC/Patchworks commands from the
same Linux environment while the VPN session is active.

CLI OpenConnect Pattern
-----------------------

Based on the uploaded UBC GNU/Linux myVPN guide:

.. code-block:: bash

   sudo openconnect myvpn.ubc.ca

Then provide credentials at prompt:

- CWL username
- CWL password
- Optional MFA suffix patterns when needed (for example ``@app`` or ``@phone``)

Keep the terminal open while connected.

Diagnostic Steps
----------------

1. Confirm VPN tunnel is active (host networking).
2. Run Patchworks preflight:

   .. code-block:: bash

      PYTHONPATH=src python -m femic patchworks preflight --config config/patchworks.runtime.yaml

3. If preflight fails, verify:

   - ``SPS_LICENSE_SERVER`` is in ``<user>@<server>`` format
   - ``SPSHOME`` is set to the Patchworks install path visible to Wine
   - Correct VPN profile/pool and MFA suffix

Failure Signatures
------------------

- ``wine64/wine not found on PATH``:
  install Wine runtime in the execution environment.
- ``Java runtime unavailable inside Wine context``:
  install/configure Windows Java runtime available to Wine.
- ``License value must use '<username>@<server>' format``:
  fix ``patchworks.license_value`` or exported env var content.
- ``Missing Patchworks install home``:
  set ``patchworks.spshome`` in runtime config or export ``SPSHOME``.

License Reachability Ownership
------------------------------

FEMIC preflight validates environment/config only. Patchworks itself performs
license-server communication at launch time.

Fallback Path
-------------

In-container OpenConnect can be used only where container runtime permits
``/dev/net/tun`` and required capabilities. Host VPN passthrough remains the
recommended default.
