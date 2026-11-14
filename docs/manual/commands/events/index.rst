.. _event-feed:

==========
Event feed
==========

The event feed publishes qtile's :ref:`hooks <ref-hooks>` to external programs
as they fire. Any program that can connect to a Unix socket and parse JSON can
subscribe, for example a status bar, a logger, or a script that reacts to new
windows.

The feed is read-only: nothing a client can send changes qtile's state. To
*act* on qtile, use the :ref:`command interfaces <scripting-interfaces>`.

Quick start
===========

``qtile events`` connects to the feed and prints one JSON object per line:

.. code:: bash

    # Everything
    qtile events

    # Only some events
    qtile events -e client_new,client_killed

    # Names of new windows (jq reads the stream line by line)
    qtile events -e client_new | jq -r '.args[0].name'

Any socket tool works too. A subscription is a single line of JSON:

.. code:: bash

    { echo '{"type": "subscribe", "events": ["client_new"]}'; cat; } \
        | socat - UNIX-CONNECT:"$HOME/.cache/qtile/qtilesocket.:0.events"

Protocol
========

Conventions
-----------

The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT" and "MAY" are to be
interpreted as described in :rfc:`2119` and :rfc:`8174`.

"JSON" means JSON as defined by :rfc:`8259`. Messages are also intended to be
valid *I-JSON* (:rfc:`7493`): member names within an object are unique,
strings are valid Unicode, and numbers are finite.

Transport
---------

The feed is a stream-oriented (``SOCK_STREAM``) Unix domain socket. Its default
path is qtile's IPC socket path with ``.events`` appended, for example
``~/.cache/qtile/qtilesocket.:0.events``.

Any number of clients may connect at once. Each connection is independent and
has its own event filter.

Framing
-------

Messages are framed as `JSON Lines <https://jsonlines.org>`_ (also known as
newline-delimited JSON), in both directions:

* A message is exactly one JSON text, and it MUST be a JSON object.
* Messages are encoded as UTF-8, without a byte order mark.
* A message is terminated by a single line feed (U+000A). A message MUST NOT
  contain a literal line feed; line feeds inside strings are escaped as ``\n``
  as usual.
* Receivers SHOULD accept a carriage return (U+000D) before the line feed, and
  SHOULD ignore empty lines.

Servers MUST emit valid JSON. In particular they MUST NOT emit ``NaN``,
``Infinity`` or ``-Infinity``, which are not JSON. The reference
implementation writes only ASCII, escaping every other character as ``\uXXXX``;
clients MUST accept any valid JSON string encoding.

Message types
-------------

Every message, in both directions, is a JSON object with a ``type`` member: a
string naming the kind of message. The other members depend on the type.

Receivers (clients and servers) MUST ignore messages whose ``type`` they do not
recognise, and MUST ignore members they do not recognise. This lets new message
types and new members be added without breaking existing programs. See
`Versioning`_.

.. list-table::
    :header-rows: 1
    :widths: 20 20 60

    * - ``type``
      - Direction
      - Purpose
    * - ``hello``
      - server to client
      - Greeting with the protocol version. Always the first message.
    * - ``event``
      - server to client
      - A hook was fired.
    * - ``subscribe``
      - client to server
      - Choose which events to receive.

Server messages
---------------

``hello``
~~~~~~~~~

The first message on every connection. It is sent immediately on connect and is
not affected by the event filter.

.. code:: json

    {"type": "hello", "version": 1}

.. list-table::
    :header-rows: 1
    :widths: 15 15 70

    * - Member
      - Type
      - Description
    * - ``version``
      - integer
      - Required. The protocol version (see `Versioning`_).

``event``
~~~~~~~~~

Reports that a hook fired.

.. code:: json

    {"type": "event", "event": "client_new", "args": [{"wid": 8388609, "name": "xterm", "group": "a"}]}
    {"type": "event", "event": "setgroup", "args": []}

.. list-table::
    :header-rows: 1
    :widths: 15 15 70

    * - Member
      - Type
      - Description
    * - ``event``
      - string
      - Required. The hook's name, for example ``client_new``, or a
        ``user_``-prefixed name for a user-defined hook. Never empty.
    * - ``args``
      - array
      - Required. The positional arguments the hook was fired with, encoded as
        described in `Value encoding`_. Empty if there were none.
    * - ``kwargs``
      - object
      - Optional. Present only if the hook was fired with keyword arguments,
        in which case it maps each name to its encoded value.

The available events and the meaning of their arguments are those of
:ref:`qtile's hooks <ref-hooks>`.

Client messages
---------------

``subscribe``
~~~~~~~~~~~~~

Replaces the event filter of the connection.

.. code:: json

    {"type": "subscribe", "events": ["client_new", "setgroup"]}
    {"type": "subscribe", "events": ["*"]}
    {"type": "subscribe", "events": null}

.. list-table::
    :header-rows: 1
    :widths: 15 15 70

    * - Member
      - Type
      - Description
    * - ``events``
      - array of strings, or ``null``
      - Required. The event names to receive.

.. list-table::
    :header-rows: 1
    :widths: 40 60

    * - Value of ``events``
      - Effect
    * - array of event names
      - Receive only events with exactly those names.
    * - array containing ``"*"``, or ``null``
      - Receive all events. This is the state of a new connection.
    * - ``[]``
      - Receive no events.

A ``subscribe`` message *replaces* the connection's filter; it does not add to
it. To widen a filter, send the full new list.

* Names are not validated. A name that is not a known event is not an error; it
  simply never matches.
* The server sends no acknowledgement.
* Events already queued before the server processes the message may still arrive
  unfiltered. Clients SHOULD therefore also filter locally.
* A message that is not valid JSON, is not an object, has an unrecognised
  ``type``, or has a missing or invalid ``events`` member (neither ``null`` nor
  an array of strings) is ignored. The connection stays open and the previous
  filter stays in force.

Delivery semantics
------------------

* **Ordering.** Events are delivered to a client in the order they were fired.
* **Best effort.** Delivery is at-most-once. There is no replay: events fired
  before a client connected, or while it was disconnected, are never delivered,
  and the feed does not send the current state. To get a consistent view,
  subscribe first and then query the current state through the
  :ref:`command interfaces <scripting-interfaces>`, so no change falls between
  the two.
* **Timing.** The payload is encoded when the hook fires, so it reflects qtile's
  state at that moment, before any callbacks from the user's configuration run.
* **Slow clients.** If more than 256 KiB of data is waiting to be sent to a
  client, the server closes that connection immediately and discards the unsent
  data, with no notice. Other clients are not affected.
* **Reconnection.** Clients MUST be prepared for the connection to end at any
  time (slow-client eviction, qtile restarting or exiting). They SHOULD
  reconnect with a back-off and re-read any state they need.
* **Reloads.** Reloading the configuration does not close connections or reset
  filters.

Limits
------

Servers MUST accept client messages of up to 65,536 bytes (excluding the line
feed). Servers SHOULD close the connection if a longer message is received.

No maximum is defined for server messages. Clients SHOULD NOT impose a small
fixed line-length limit.

Versioning
----------

The ``version`` in the ``hello`` message is an integer, currently ``1``.

It increases only for incompatible changes: removing or renaming a message type
or member, changing the meaning or type of a member, or changing the framing.
The following are *not* incompatible and do not change the version:

* new message types, in either direction (see `Message types`_),
* new members in any message or object,
* new events (new hooks) and new qtile object types in payloads.

Clients SHOULD read the version and warn or exit if it is higher than the
version they were written for.

Because events are qtile's hooks, their names and arguments can change between
qtile releases in the same way hooks can.

Value encoding
==============

Hook arguments are Python objects. They are converted to JSON as follows:

.. list-table::
    :header-rows: 1
    :widths: 35 65

    * - Python value
      - JSON
    * - ``None``
      - ``null``
    * - ``bool``
      - ``true`` / ``false``
    * - ``int``
      - number (integer, exact)
    * - ``float``
      - number. ``NaN`` and infinities are encoded as ``null``.
    * - ``str``
      - string. Unpaired surrogates, which can occur in names read from
        applications, are replaced with U+FFFD.
    * - ``list``, ``tuple``, ``set``
      - array. The order of a set's members is unspecified.
    * - ``dict``
      - object. Keys are converted with ``str()`` and treated like any other
        string; if two keys collide, one value is lost.
    * - qtile objects listed below
      - object with the members given below
    * - anything else
      - string containing ``repr()`` of the value. This text is not a stable
        format and MUST NOT be parsed.

Arrays and objects nested more than five levels deep inside an argument are
replaced by their ``repr()`` string.

Integers are emitted exactly. A client that reads JSON numbers as IEEE 754
doubles (JavaScript, for example) loses precision above 2\ :sup:`53`; the
identifiers qtile emits are expected to be well below that.

qtile objects
-------------

.. list-table::
    :header-rows: 1
    :widths: 15 85

    * - Object
      - Members
    * - window
      - ``wid`` (integer): identifier, unique for the lifetime of the session.
        ``name`` (string, or ``null`` if unavailable): the window's title.
        ``group`` (string or ``null``): name of the group the window is in.
    * - group
      - ``name`` (string). ``windows`` (array of window objects).
        ``screen`` (screen object or ``null``).
    * - screen
      - ``index`` (integer).
    * - layout
      - ``name`` (string).

These objects may gain members (see `Versioning`_). Clients MUST ignore members
they do not know.

Security considerations
=======================

The feed exposes window titles and other desktop state. Window titles often
contain private information, such as the page a browser is showing or a
document's file name.

* There is no authentication or encryption. Access control is the permission
  of the socket in the filesystem. The server SHOULD create the socket
  accessible by its owner only (mode ``0600``) in a directory other users
  cannot enter. On Linux it MAY also check the peer's user ID with
  ``SO_PEERCRED``.
* Strings such as window titles are controlled by whichever application owns
  the window. Clients MUST treat them as untrusted data: never pass them to a
  shell, interpolate them into markup or SQL, or use them as file names without
  validation.
* The feed is read-only, so a client cannot use it to change qtile.

Examples
========

A short session. Lines starting with ``<`` are sent by the server and lines
starting with ``>`` by the client.

.. code:: text

    < {"type": "hello", "version": 1}
    < {"type": "event", "event": "setgroup", "args": []}
    > {"type": "subscribe", "events": ["client_new"]}
    < {"type": "event", "event": "client_new", "args": [{"wid": 8388609, "name": "xterm", "group": "a"}]}

A minimal client in Python:

.. code:: python

    import json
    import socket

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect("/path/to/qtilesocket.:0.events")

    with sock.makefile("rw", encoding="utf-8", newline="\n") as stream:
        subscribe = {"type": "subscribe", "events": ["client_new"]}
        stream.write(json.dumps(subscribe) + "\n")
        stream.flush()
        for line in stream:
            message = json.loads(line)
            if message["type"] == "hello":
                if message["version"] != 1:
                    raise SystemExit("unsupported event feed version")
            elif message["type"] == "event":
                print(message["event"], message["args"])
            # Other types come from newer servers: ignore them.

JSON Schema
===========

These schemas (JSON Schema 2020-12) describe the messages. They are
informative; the text above is normative. Message types the schemas do not
describe are valid, because receivers ignore them. Because the ``args`` of an
event depend on the hook, the server schema does not constrain their contents.
The definitions under ``$defs`` describe the qtile objects that may appear
inside ``args``.

Server to client:

.. code:: json

    {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "title": "qtile event feed: server message",
      "type": "object",
      "required": ["type"],
      "properties": {"type": {"type": "string"}},
      "allOf": [
        {
          "if": {"properties": {"type": {"const": "hello"}}},
          "then": {
            "required": ["version"],
            "properties": {"version": {"type": "integer", "minimum": 1}}
          }
        },
        {
          "if": {"properties": {"type": {"const": "event"}}},
          "then": {
            "required": ["event", "args"],
            "properties": {
              "event": {"type": "string", "minLength": 1},
              "args": {"type": "array"},
              "kwargs": {"type": "object"}
            }
          }
        }
      ],
      "$defs": {
        "window": {
          "type": "object",
          "required": ["wid", "name", "group"],
          "properties": {
            "wid": {"type": "integer"},
            "name": {"type": ["string", "null"]},
            "group": {"type": ["string", "null"]}
          }
        },
        "group": {
          "type": "object",
          "required": ["name", "windows", "screen"],
          "properties": {
            "name": {"type": "string"},
            "windows": {"type": "array", "items": {"$ref": "#/$defs/window"}},
            "screen": {"oneOf": [{"$ref": "#/$defs/screen"}, {"type": "null"}]}
          }
        },
        "screen": {
          "type": "object",
          "required": ["index"],
          "properties": {"index": {"type": "integer"}}
        },
        "layout": {
          "type": "object",
          "required": ["name"],
          "properties": {"name": {"type": "string"}}
        }
      }
    }

Client to server:

.. code:: json

    {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "title": "qtile event feed: client message",
      "type": "object",
      "required": ["type"],
      "properties": {"type": {"type": "string"}},
      "allOf": [
        {
          "if": {"properties": {"type": {"const": "subscribe"}}},
          "then": {
            "required": ["events"],
            "properties": {
              "events": {"type": ["array", "null"], "items": {"type": "string"}}
            }
          }
        }
      ]
    }
