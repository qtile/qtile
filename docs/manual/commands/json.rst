=================
JSON IPC Protocol
=================

This document details the architecture, framing, envelope, and message definitions of Qtile's JSON-based IPC protocol.

Overview & Transport
====================

Qtile's IPC mechanism operates using **Unix Domain Sockets** (``socket.AF_UNIX``).

Socket Discovery
----------------

By default, the client determines the appropriate socket file path in Qtile's cache directory according to the following precedence rule (``libqtile.ipc.find_sockfile``):

1. An explicitly provided display parameter.
2. The ``WAYLAND_DISPLAY`` environment variable.
3. The ``DISPLAY`` environment variable.
4. Fallback check for the existence of ``wayland-0``.
5. Fallback check for the existence of ``:0``.

The resulting socket path follows this template: **qtilesocket.display**

Framing Protocol
----------------

Connections to the Unix domain socket are framed using a binary header:

* **Header (4 bytes):** Unsigned 32-bit integer in network byte order (big-endian, struct format ``!L``) specifying the byte length of the following payload.
* **Payload:** UTF-8 encoded JSON payload matching the exact length specified by the header.

Python code can use the ``libqtile.ipc.stream.IPCStreamIO`` wrapper for asyncio's ``StreamReader`` and ``StreamWriter`` objects. The wrapper has methods for
reading and writing messages which will automatically handle the framing protocol.

Message Envelope & Serialization
================================

Every frame transmitted across the wire encapsulates a top-level JSON message envelope:

.. code-block:: json

   {
     "message_type": "<type_string>",
     "content": {
       ...
     }
   }

Data Type Mappings
------------------

Because standard JSON does not natively support Python tuple or set types, custom serialization rules are applied:

* **Tuples:** Encoded as objects with a single ``$tuple`` key holding an array. Example: ``{"$tuple": [1, 2]}``.
* **Sets:** Automatically transformed into JSON arrays.

Message Schemas
===============

Client -> Server Messages
-------------------------

Command (``command``)
~~~~~~~~~~~~~~~~~~~~~

Invokes a command on Qtile objects.

* **message_type:** ``command``
* **Content:**

  .. code-block:: json

     {
       "selectors": [],
       "name": "command_name",
       "args": [],
       "kwargs": {},
       "lifted": false
     }

REPL Start (``repl_start``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Requests the creation of a new interactive Python REPL session.

* **message_type:** ``repl_start``
* **Content:** ``{}``

REPL Stop (``repl_stop``)
~~~~~~~~~~~~~~~~~~~~~~~~~

Terminates an active REPL session.

* **message_type:** ``repl_stop``
* **Content:**

  .. code-block:: json

     {
       "session_id": "3a0b1c2d..."
     }

REPL Request (``repl_request``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sends a code snippet for evaluation or an auto-completion query to a REPL session.

* **Code Evaluation Content:**

  .. code-block:: json

     {
       "session_id": "3a0b1c2d...",
       "code": "qtile.current_window.name"
     }

* **Completion Query Content:**

  .. code-block:: json

     {
       "session_id": "3a0b1c2d...",
       "completion": "qtile.win"
     }

Events Subscribe (``events_subscribe``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Subscribes the current connection to Qtile hook events.

* **message_type:** ``events_subscribe``
* **Content:**

  .. code-block:: json

     {
       "events": ["client_new", "setgroup"]
     }

  *(Setting ``"events": null`` or ``"events": ["*"]`` subscribes to all events.)*

Events Unsubscribe (``events_unsubscribe``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unsubscribes the current connection from receiving hook events.

* **message_type:** ``events_unsubscribe``
* **Content:** ``{}``

Server -> Client Messages
-------------------------

Reply (``reply``)
~~~~~~~~~~~~~~~~~

Returned in response to client-initiated requests. All replies follow a unified payload wrapper:

.. code-block:: json

   {
     "status": 0,
     "data": null
   }

The payload structure inside ``data`` varies depending on the initial request:

* **REPL Start Payload (``repl_start``):**

  Returns the newly allocated session identifier and a greeting header.

  .. code-block:: json

     {
       "status": 0,
       "data": {
         "session_id": "c1f7a0b3...",
         "output": "Connected to Qtile REPL\nPress Ctrl+C to exit.\n"
       }
     }

* **REPL Code Execution Payload (``repl_request`` with ``code``):**

  Returns stdout/stderr output captured during snippet execution.

  .. code-block:: json

     {
       "status": 0,
       "data": {
         "output": "Result string or stdout content"
       }
     }

* **REPL Autocomplete Payload (``repl_request`` with ``completion``):**

  Returns matching attribute/variable names for the requested prefix.

  .. code-block:: json

     {
       "status": 0,
       "data": {
         "matches": [
           "qtile.windows",
           "qtile.windows_map"
         ]
       }
     }

* **REPL Stop Payload (``repl_stop``):**

  .. code-block:: json

     {
       "status": 0,
       "data": "Client disconnected."
     }

Events Notify (``events_notify``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Asynchronously pushed to subscribed clients when a Qtile hook fires.

* **message_type:** ``events_notify``
* **Content:**

  .. code-block:: json

     {
       "event_name": "client_new",
       "args": [],
       "kwargs": {}
     }

Status Codes & Errors
=====================

The ``status`` field in a ``reply`` message indicates the operational result:

.. list-table::
   :header-rows: 1
   :widths: 15 20 65

   * - Status Code
     - Name
     - Description
   * - ``0``
     - ``SUCCESS``
     - Request processed successfully. The ``data`` key holds the return payload.
   * - ``1``
     - ``ERROR``
     - A logic or system error occurred (e.g., locked session or missing/invalid ID).
   * - ``2``
     - ``EXCEPTION``
     - An unhandled Python exception occurred. The ``data`` key contains the formatted traceback string array.
