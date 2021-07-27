SCHEMA_DBUS_MENU = """
<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
"http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
<interface name="com.canonical.dbusmenu">
    <!-- Properties -->
    <property name="Version" type="u" access="read" />
    <property name="TextDirection" type="s" access="read" />
    <property name="Status" type="s" access="read" />
    <property name="IconThemePath" type="as" access="read" />

    <!-- Functions -->
    <method name="GetLayout">
        <arg type="i" name="parentId" direction="in" />
        <arg type="i" name="recursionDepth" direction="in" />
        <arg type="as" name="propertyNames" direction="in" />
        <arg type="u" name="revision" direction="out" />
        <arg type="(ia{sv}av)" name="layout" direction="out" />
    </method>

    <method name="GetGroupProperties">
        <arg type="ai" name="ids" direction="in" />
        <arg type="as" name="propertyNames" direction="in" />
        <arg type="a(ia{sv})" name="properties" direction="out" />
    </method>

    <method name="GetProperty">
        <arg type="i" name="id" direction="in" />
        <arg type="s" name="name" direction="in" />
        <arg type="v" name="value" direction="out" />
    </method>

    <method name="Event">
        <arg type="i" name="id" direction="in" />
        <arg type="s" name="eventId" direction="in" />
        <arg type="v" name="data" direction="in" />
        <arg type="u" name="timestamp" direction="in" />
    </method>

    <method name="EventGroup">
        <arg type="a(isvu)" name="events" direction="in" />
        <arg type="ai" name="idErrors" direction="out" />
    </method>

    <method name="AboutToShow">
        <arg type="i" name="id" direction="in" />
        <arg type="b" name="needUpdate" direction="out" />
    </method>

    <method name="AboutToShowGroup">
        <arg type="ai" name="ids" direction="in" />
        <arg type="ai" name="updatesNeeded" direction="out" />
        <arg type="ai" name="idErrors" direction="out" />
    </method>

    <!-- Signals -->
    <signal name="ItemsPropertiesUpdated">
        <arg type="a(ia{sv})" name="updatedProps" direction="out" />
        <arg type="a(ias)" name="removedProps" direction="out" />
    </signal>
    <signal name="LayoutUpdated">
        <arg type="u" name="revision" direction="out" />
        <arg type="i" name="parent" direction="out" />
    </signal>
    <signal name="ItemActivationRequested">
        <arg type="i" name="id" direction="out" />
        <arg type="u" name="timestamp" direction="out" />
    </signal>
</interface>
</node>
"""   # noqa: E501
