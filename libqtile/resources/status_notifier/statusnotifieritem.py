SCHEMA_STATUS_NOTIFIER_ITEM = """
<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.kde.StatusNotifierItem">

    <property name="Category" type="s" access="read"/>

    <property name="Id" type="s" access="read"/>

    <property name="Title" type="s" access="read"/>

    <property name="Status" type="s" access="read"/>

    <property name="WindowId" type="i" access="read"/>

    <property name="IconThemePath" type="s" access="read"/>

    <property name="Menu" type="o" access="read"/>

    <property name="ItemIsMenu" type="b" access="read"/>

    <property name="IconName" type="s" access="read"/>

    <property name="IconPixmap" type="a(iiay)" access="read">
      <annotation name="org.qtproject.QtDBus.QtTypeName" value="IconPixmapList"/>
    </property>

    <property name="OverlayIconName" type="s" access="read"/>

    <property name="OverlayIconPixmap" type="a(iiay)" access="read">
      <annotation name="org.qtproject.QtDBus.QtTypeName" value="IconPixmapList"/>
    </property>

    <property name="AttentionIconName" type="s" access="read"/>

    <property name="AttentionIconPixmap" type="a(iiay)" access="read">
      <annotation name="org.qtproject.QtDBus.QtTypeName" value="IconPixmapList"/>
    </property>

    <property name="AttentionMovieName" type="s" access="read"/>

    <property name="ToolTip" type="(sa(iiay)ss)" access="read">
      <annotation name="org.qtproject.QtDBus.QtTypeName" value="ToolTip"/>
    </property>

    <method name="ContextMenu">
        <arg name="x" type="i" direction="in"/>
        <arg name="y" type="i" direction="in"/>
    </method>

    <method name="Activate">
        <arg name="x" type="i" direction="in"/>
        <arg name="y" type="i" direction="in"/>
    </method>

    <method name="SecondaryActivate">
        <arg name="x" type="i" direction="in"/>
        <arg name="y" type="i" direction="in"/>
    </method>

    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>

    <signal name="NewTitle">
    </signal>

    <signal name="NewIcon">
    </signal>

    <signal name="NewAttentionIcon">
    </signal>

    <signal name="NewOverlayIcon">
    </signal>

    <signal name="NewToolTip">
    </signal>

    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>

  </interface>
</node>
"""  # noqa: E501
