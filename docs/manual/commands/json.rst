=======================
Qtile JSON IPC Protocol
=======================

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

The resulting socket path follows this template: ``qtilesocket.<display>``

Framing Protocol
----------------

Connections to the Unix domain socket are framed using a binary header:

* **Header (4 bytes):** Unsigned 32-bit integer in network byte order (big-endian, struct format ``!L``) specifying the byte length of the following payload.
* **Payload:** UTF-8 encoded JSON payload matching the exact length specified by the header.

Python code can use the ``libqtile.ipc.stream.IPCStreamIO`` wrapper for asyncio's ``StreamReader`` and ``StreamWriter`` objects. The wrapper has methods for
reading and writing messages which will automatically handle the framing protocol.

Message Envelope & Serialization
================================

Every frame transmitted across the wire encapsulates a top-level JSON message envelope containing a discriminator and content block:

.. code-block:: json

   {
     "message_type": "<type_string>",
     "content": {
       ...
     }
   }

Protocol Structure
------------------

Communication follows a **Request-Reply** model for most actions, alongside a **Publish-Subscribe** model for event broadcasting:

* **Requests:** Sent by the client to the server containing a specific ``message_type`` and its corresponding ``content`` dictionary.
* **Replies:** Sent by the server in response to every request using the ``"reply"`` message type. The reply contains a status indicator (0 for success, 1 for error, 2 for unhandled exception) and a ``data`` field containing the response payload or error message.
* **Notifications:** Asynchronous push messages (``"events_notify"``) sent from server to client following an active event subscription.

Data Type Mappings
------------------

Because standard JSON does not natively support Python tuple or set types, custom serialization rules are applied:

* **Tuples:** Encoded as objects with a single ``$tuple`` key holding an array. Example: ``{"$tuple": [1, 2]}``
* **Sets:** Automatically transformed into JSON arrays.

IPC Message Interfaces
======================

Command System
--------------

Executes functions and methods on Qtile targets (e.g. windows, layouts, groups).

Request: ``command``
~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "message_type": "command",
     "content": {
       "selectors": [],
       "name": "command_name",
       "args": [],
       "kwargs": {},
       "lifted": false
     }
   }

Reply Payload
~~~~~~~~~~~~~

Returns the output of the executed command.

.. code-block:: json

   {
     "message_type": "reply",
     "content": {
       "status": 0,
       "data": "result_value"
     }
   }

REPL System
-----------

Provides an interactive Python REPL session for inspecting and interacting with Qtile internals.

1. Start REPL Session
~~~~~~~~~~~~~~~~~~~~~

**Request (``repl_start``):**

.. code-block:: json

   {
     "message_type": "repl_start",
     "content": {}
   }

**Reply Payload:**

Returns a generated ``session_id`` (UUID string) and a greeting string.

.. code-block:: json

   {
     "message_type": "reply",
     "content": {
       "status": 0,
       "data": {
         "session_id": "c1f7a0b3e2a14b0380f58cd2e71d42a8",
         "output": "Connected to Qtile REPL\nPress Ctrl+C to exit.\n"
       }
     }
   }

2. REPL Requests
~~~~~~~~~~~~~~~~

**Code Evaluation Request (``repl_request``):**

.. code-block:: json

   {
     "message_type": "repl_request",
     "content": {
       "session_id": "c1f7a0b3e2a14b0380f58cd2e71d42a8",
       "code": "qtile.current_window.name"
     }
   }

*Code Evaluation Reply Payload:*

.. code-block:: json

   {
     "message_type": "reply",
     "content": {
       "status": 0,
       "data": {
         "output": "'Terminal'\n"
       }
     }
   }

**Completion Request (``repl_request``):**

.. code-block:: json

   {
     "message_type": "repl_request",
     "content": {
       "session_id": "c1f7a0b3e2a14b0380f58cd2e71d42a8",
       "completion": "qtile.win"
     }
   }

*Completion Reply Payload:*

.. code-block:: json

   {
     "message_type": "reply",
     "content": {
       "status": 0,
       "data": {
         "matches": [
           "qtile.windows",
           "qtile.windows_map"
         ]
       }
     }
   }

3. Stop REPL Session
~~~~~~~~~~~~~~~~~~~~

**Request (``repl_stop``):**

.. code-block:: json

   {
     "message_type": "repl_stop",
     "content": {
       "session_id": "c1f7a0b3e2a14b0380f58cd2e71d42a8"
     }
   }

**Reply Payload:**

.. code-block:: json

   {
     "message_type": "reply",
     "content": {
       "status": 0,
       "data": "Client disconnected."
     }
   }

Event Subscriptions
-------------------

Subscribes connections to real-time Qtile hook event broadcasts.

1. Subscribe to Events
~~~~~~~~~~~~~~~~~~~~~~

**Request (``events_subscribe``):**

.. code-block:: json

   {
     "message_type": "events_subscribe",
     "content": {
       "events": ["client_new", "setgroup"]
     }
   }

*Note: Passing ``"events": null`` or ``"events": []`` subscribes to all available hooks.*

**Reply Payload:**

.. code-block:: json

   {
     "message_type": "reply",
     "content": {
       "status": 0,
       "data": "Subscribe successful."
     }
   }

2. Event Notification (Server Broadcast)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Asynchronous push message sent from server to client when a subscribed hook fires.

**Notification Message (``events_notify``):**

.. code-block:: json

   {
     "message_type": "events_notify",
     "content": {
       "event_name": "client_new",
       "args": [
         {
           "wid": 12582914,
           "name": "Alacritty",
           "group": "1"
         }
       ],
       "kwargs": {}
     }
   }

3. Unsubscribe from Events
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Request (``events_unsubscribe``):**

.. code-block:: json

   {
     "message_type": "events_unsubscribe",
     "content": {}
   }

**Reply Payload:**

.. code-block:: json

   {
     "message_type": "reply",
     "content": {
       "status": 0,
       "data": "Unsubscribe successful."
     }
   }

Status Codes & Exception Handling
=================================

The ``status`` field inside reply messages indicates the execution status:

.. list-table::
   :header-rows: 1
   :widths: 15 20 65

   * - Status Code
     - Enum Name
     - Description
   * - ``0``
     - ``SUCCESS``
     - Request processed successfully. The ``data`` field holds the result object/value.
   * - ``1``
     - ``ERROR``
     - A system or logic error occurred (e.g. invalid session ID, locked session).
   * - ``2``
     - ``EXCEPTION``
     - An unhandled Python exception was raised during execution. The ``data`` field contains the formatted traceback string array.
