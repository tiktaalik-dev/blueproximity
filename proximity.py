#!/usr/bin/env python
# coding: utf-8

SW_VERSION = '1.3.3'

# Add security to your desktop by automatically locking and unlocking 
# the screen when you and your phone leave/enter the desk. 
# Think of a proximity detector for your mobile phone via bluetooth.
# requires external bluetooth util hcitool to run
# (which makes it unix only at this time)

# Needed python extensions:
#  ConfigObj (python3-configobj)
#  PyGTK3 (python3-gi)
#  Bluetooth (python-bluez)

# copyright by Lars Friedrichs <larsfriedrichs@gmx.de>
# this source is licensed under the GPL.
# I'm a big fan of talkback about how it performs!
# I'm also open to feature requests and notes on programming issues, I am no python master at all...
# ToDo List can be found on sourceforge
# follow http://blueproximity.sourceforge.net

APP_NAME = "blueproximity"

# This value gives us the base directory for language files and icons.
# Set this value to './' for local folder version
# or, for instance, to '/usr/share/blueproximity/' for packaged version
dist_path = './'

# Translation stuff
import gettext
import locale

# system includes
import os
import signal
import sys
import syslog
import threading
import time

# blueproximity
import struct

# Get the local directory since we are not installing anything
if dist_path == './':
    dist_path = os.path.dirname(os.path.abspath(__file__)) + '/'

# Init the list of languages to support
local_path = dist_path + 'LANG/'
langs = []

# Check the default locale
lc, encoding = locale.getdefaultlocale()

if lc:
    # If we have a default, it's the first in the list
    langs = [lc]

# Now lets get all of the supported languages on the system
language = os.environ.get('LANGUAGE', None)

if language:
    # Language comes back something like en_CA:en_US:en_GB:en
    # on linux systems, on Win32 it's nothing, so we need to
    # split it up into a list
    langs += language.split(":")

# Now add on to the back of the list the translations that we
# know that we have, our defaults
langs += ["en"]

# Now langs is a list of all of the languages that we are going
# to try to use.  First we check the default, then what the system
# told us, and finally the 'known' list
gettext.bindtextdomain(APP_NAME, local_path)
gettext.textdomain(APP_NAME)

# Get the language to use
lang = gettext.translation(APP_NAME, local_path, languages=langs, fallback=True)

# Install the language, map _() (which we marked our
# strings to translate with) to self.lang.gettext() which will
# translate them.
_ = lang.gettext

# now the imports from external packages
try:
    import gi

    gi.require_version('Gtk', '3.0')
    from gi.repository import GObject as gobject
except:
    print(_("The program cannot import the module gobject."))
    print(_("Please make sure the GObject bindings for python are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python3-gi"))
    sys.exit(1)

try:
    gi.require_version('XApp', '1.0')
    from gi.repository import XApp
except:
    print(_("The program cannot import the module XApp."))
    print(_("Please make sure the GI bindings for XApp are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install gir1.2-xapp-1.0"))
    sys.exit(1)

try:
    from configobj import ConfigObj
    from validate import Validator
except:
    print(_("The program cannot import the module ConfigObj or Validator."))
    print(_("Please make sure the ConfigObject package for python is installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python3-configobj"))
    sys.exit(1)

IMPORT_BT = 0

try:
    import bluetooth

    IMPORT_BT = IMPORT_BT + 1
except:
    pass

try:
    import _bluetooth as bluez

    IMPORT_BT = IMPORT_BT + 1
except:
    pass

try:
    import bluetooth._bluetooth as bluez

    IMPORT_BT = IMPORT_BT + 1
except:
    pass

if (IMPORT_BT != 2):
    print(_("The program cannot import the module bluetooth."))
    print(_("Please make sure the bluetooth bindings for python as well as bluez are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python3-bluez"))
    sys.exit(1)

try:
    from gi.repository import Gtk as gtk
except:
    print(_("The program cannot import the module pygtk."))
    print(_("Please make sure the GTK3 bindings for python are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python3-gi"))
    sys.exit(1)

try:
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf
except:
    print(_("The program cannot import the module GdkPixbuf."))
    print(_("Please make sure the GTK3 bindings for python are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python3-gi"))
    sys.exit(1)

try:
    builder = gtk.Builder()
    gtk.glade = builder
except:
    print(_("The program cannot import the module Builder (former glade)."))
    print(_("Please make sure the Glade3 bindings for python are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python3-gi"))
    sys.exit(1)

# Setup config file specs and defaults
# This is the ConfigObj's syntax
conf_specs = [
    'device_mac=string(max=17,default="")',
    'device_channel=integer(1,30,default=7)',
    'lock_distance=integer(0,127,default=7)',
    'lock_duration=integer(0,120,default=6)',
    'unlock_distance=integer(0,127,default=4)',
    'unlock_duration=integer(0,120,default=1)',
    'lock_command=string(default=''gnome-screensaver-command -l'')',
    'unlock_command=string(default=''gnome-screensaver-command -d'')',
    'proximity_command=string(default=''gnome-screensaver-command -p'')',
    'proximity_interval=integer(5,600,default=60)',
    'buffer_size=integer(1,255,default=1)',
    'log_to_syslog=boolean(default=True)',
    'log_syslog_facility=string(default=''local7'')',
    'log_to_file=boolean(default=False)',
    'log_filelog_filename=string(default=''' + os.getenv('HOME') + '/blueproximity.log'')'
]

# The icon used at normal operation and in the info dialog.
icon_base = 'blueproximity_base.svg'
# The icon used at distances greater than the unlock distance.
icon_att = 'blueproximity_attention.svg'
# The icon used if no proximity is detected.
icon_away = 'blueproximity_nocon.svg'
# The icon used during connection processes and with connection errors.
icon_error = 'blueproximity_error.svg'
# The icon shown if we are in pause mode.
icon_pause = 'blueproximity_pause.svg'


# Note (17/08/2020 - Rodrigo Gambra-Middleton): This helper function was absent in the original code even though it was
# called in specifically! I thought it might have been part of the bluetooth library, but it wasn't. Then I found it
# in a similar BT program at:
# https://www.programcreek.com/python/example/92269/bluetooth._bluetooth.hci_filter_all_events
def printpacket(pkt):
    for c in pkt:
        sys.stdout.write("%02x " % struct.unpack("B", c)[0])


# This class represents the main configuration window and
# updates the config file after changes made are saved
class ProximityGUI(object):

    # Constructor sets up the GUI and reads the current config
    # @param configs A list of lists of name, ConfigObj object, proximity object
    # @param show_window_on_start Set to True to show the config screen immediately after the start.
    # This is true if no prior config file has been detected (initial start).
    def __init__(self, configs, show_window_on_start):

        # This is to block events from firing a config write because we initialy set a value
        self.gone_live = False

        # Set the Glade file
        self.gladefile = dist_path + "proximity3.glade"
        self.wTree = gtk.glade.new_from_file(self.gladefile)

        # Create our dictionary and connect it
        dic = {"on_btnInfo_clicked": self.aboutPressed,
               "on_btnClose_clicked": self.btnClose_clicked,
               "on_btnNew_clicked": self.btnNew_clicked,
               "on_btnDelete_clicked": self.btnDelete_clicked,
               "on_btnRename_clicked": self.btnRename_clicked,
               "on_comboConfig_changed": self.comboConfig_changed,
               "on_btnScan_clicked": self.btnScan_clicked,
               "on_btnScanChannel_clicked": self.btnScanChannel_clicked,
               "on_btnSelect_clicked": self.btnSelect_clicked,
               "on_btnResetMinMax_clicked": self.btnResetMinMax_clicked,
               "on_settings_changed": self.event_settings_changed,
               "on_settings_changed_reconnect": self.event_settings_changed_reconnect,
               "on_treeScanChannelResult_changed": self.event_scanChannelResult_changed,
               "on_btnDlgNewDo_clicked": self.dlgNewDo_clicked,
               "on_btnDlgNewCancel_clicked": self.dlgNewCancel_clicked,
               "on_btnDlgRenameDo_clicked": self.dlgRenameDo_clicked,
               "on_btnDlgRenameCancel_clicked": self.dlgRenameCancel_clicked,
               "on_MainWindow_destroy": self.btnClose_clicked}
        self.wTree.connect_signals(dic)

        # Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_object("MainWindow")
        if self.window:
            self.window.connect("delete_event", self.btnClose_clicked)
        from gi.repository import GdkPixbuf
        pixbuf_img = GdkPixbuf.Pixbuf.new_from_file(dist_path + icon_base)
        self.window.set_icon(pixbuf_img)
        self.proxi = configs[0][2]
        self.minDist = -255
        self.maxDist = 0
        self.pauseMode = False
        self.lastMAC = ''
        self.scanningChannels = False

        # Get the New Config Window, and connect the "destroy" event
        self.windowNew = self.wTree.get_object("createNewWindow")
        if self.windowNew:
            self.windowNew.connect("delete_event", self.dlgNewCancel_clicked)

        # Get the Rename Config Window, and connect the "destroy" event
        self.windowRename = self.wTree.get_object("renameWindow")
        if self.windowRename:
            self.windowRename.connect("delete_event", self.dlgRenameCancel_clicked)

        # Prepare the mac/name table
        self.model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.tree = self.wTree.get_object("treeScanResult")
        self.tree.set_model(self.model)
        self.selection_mode = gtk.SelectionMode.SINGLE
        self.tree.get_selection().set_mode(self.selection_mode)
        colLabel = gtk.TreeViewColumn(_('MAC'), gtk.CellRendererText(), text=0)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(0)
        self.tree.append_column(colLabel)
        colLabel = gtk.TreeViewColumn(_('Name'), gtk.CellRendererText(), text=1)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(1)
        self.tree.append_column(colLabel)

        # Prepare the channel/state table
        self.modelScan = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeChan = self.wTree.get_object("treeScanChannelResult")
        self.treeChan.set_model(self.modelScan)
        colLabel = gtk.TreeViewColumn(_('Channel'), gtk.CellRendererText(), text=0)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(0)
        self.treeChan.append_column(colLabel)
        colLabel = gtk.TreeViewColumn(_('State'), gtk.CellRendererText(), text=1)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(1)
        self.treeChan.append_column(colLabel)

        # Show the current settings
        self.configs = configs
        self.configname = configs[0][0]
        self.config = configs[0][1]
        self.fillConfigCombo()
        self.readSettings()

        # this is the gui timer
        from gi.repository import GLib as glib
        self.timer = glib.timeout_add(1000, self.updateState)
        # fixme: this will execute the proximity command at the given interval - is now not working
        self.timer2 = glib.timeout_add(1000 * int(self.config['proximity_interval']), self.proximityCommand)

        # Only show if we started unconfigured
        if show_window_on_start:
            self.window.show()

        # Prepare icon
        self.icon = XApp.StatusIcon()
        self.icon.set_tooltip_text(_("BlueProximity starting..."))
        self.icon.set_icon_name(dist_path + icon_error)

        # self.icon.connect('activate', self.showWindow)
        # self.icon.connect('popup-menu', self.popupMenu, self.popupmenu)
        self.icon.connect('button-release-event', self.make_popupmenu)
        # self.icon.popup_menu(self.popupmenu, 0, 0, 0, 0, 0)

        self.icon.set_visible(True)

        # now the control may fire change events
        self.gone_live = True
        # log start in all config files
        for config in self.configs:
            config[2].logger.log_line(_('started.'))

        # Setup the popup menu and associated callbacks
    def make_popupmenu(self, first, second, third, button, event_time, unknown):
        if button == 1:
            self.showWindow(self.icon)
        if button == 3:
            self.popupmenu = gtk.Menu()
            menuItem = gtk.MenuItem.new_with_mnemonic(_("_Preferences"))
            menuItem.connect('activate', self.showWindow)
            self.popupmenu.append(menuItem)
            menuItem = gtk.MenuItem.new_with_mnemonic(_("_Pause"))
            menuItem.connect('activate', self.pausePressed)
            self.popupmenu.append(menuItem)
            menuItem = gtk.MenuItem.new_with_mnemonic(_("_About"))
            menuItem.connect('activate', self.aboutPressed)
            self.popupmenu.append(menuItem)
            menuItem = gtk.SeparatorMenuItem()
            self.popupmenu.append(menuItem)
            menuItem = gtk.MenuItem.new_with_mnemonic(_("_Quit"))
            menuItem.connect('activate', self.quit)
            self.popupmenu.append(menuItem)
            self.popupmenu.show_all()
            self.popupmenu.popup(None, None, None, 3, button, event_time)

    # Callback to just close and not destroy the rename config window
    def dlgRenameCancel_clicked(self, widget, data=None):
        self.windowRename.hide()
        return 1

    # Callback to rename a config file.
    def dlgRenameDo_clicked(self, widget, data=None):
        newconfig = self.wTree.get_widget("entryRenameName").get_text()
        # check if something has been entered
        if newconfig == '':
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    _("You must enter a name for the configuration."))
            dlg.run()
            dlg.destroy()
            return 0
        # now check if that config already exists
        newname = os.path.join(os.getenv('HOME'), '.blueproximity', newconfig + ".conf")
        try:
            os.stat(newname)
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    _("A configuration file with the name '%s' already exists.") % newname)
            dlg.run()
            dlg.destroy()
            return 0
        except:
            pass

        config = None
        for conf in self.configs:
            if (conf[0] == self.configname):
                config = conf

        # change the path of the config file
        oldfile = self.config.filename
        self.config.filename = newname
        # save it under the new name
        self.config.write()

        # delete the old file
        try:
            os.remove(oldfile)
        except:
            print(_("The configfile '%s' could not be deleted.") % oldfile)

        # change the gui name
        self.configname = newconfig

        # update the configs array
        config[0] = newconfig

        # show changes
        self.fillConfigCombo()
        self.windowRename.hide()

    # Callback to just close and not destroy the new config window
    def dlgNewCancel_clicked(self, widget, data=None):
        self.windowNew.hide()
        return 1

    # Callback to create a config file.
    def dlgNewDo_clicked(self, widget, data=None):
        newconfig = self.wTree.get_widget("entryNewName").get_text()

        # check if something has been entered
        if (newconfig == ''):
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    _("You must enter a name for the new configuration."))
            dlg.run()
            dlg.destroy()
            return 0

        # now check if that config already exists
        newname = os.path.join(os.getenv('HOME'), '.blueproximity', newconfig + ".conf")

        try:
            os.stat(newname)
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    _("A configuration file with the name '%s' already exists.") % newname)
            dlg.run()
            dlg.destroy()
            return 0
        except:
            pass

        # then let's get it on...
        # create the new config
        newconf = ConfigObj(self.config.dict())
        newconf.filename = newname

        # and save it to the new name
        newconf.write()

        # create the according Proximity object
        p = Proximity(newconf)
        p.Simulate = True
        p.start()

        # fill that into our list of active configs
        self.configs.append([newconfig, newconf, p])

        # now refresh the gui to take account of our new config
        self.config = newconf
        self.configname = newconfig
        self.proxi = p
        self.readSettings()
        self.configs.sort()
        self.fillConfigCombo()

        # close the new config dialog
        self.windowNew.hide()

    # Helper function to enable or disable the change or creation of the config files
    # This is called during non blockable functions that rely on the config not
    # being changed over the process like scanning for devices or channels
    # @param activate set to True to activate buttons, False to disable
    def setSensitiveConfigManagement(self, activate):
        # get the widget
        combo = self.wTree.get_object("comboConfig")
        combo.set_sensitive(activate)
        button = self.wTree.get_object("btnNew")
        button.set_sensitive(activate)
        button = self.wTree.get_object("btnRename")
        button.set_sensitive(activate)
        button = self.wTree.get_object("btnDelete")
        button.set_sensitive(activate)

    # Helper function to populate the list of configurations.
    def fillConfigCombo(self):

        # get the widget
        combo = self.wTree.get_object("comboConfig")
        model = combo.get_model()
        combo.set_model(None)
        # delete the list
        model.clear()
        pos = 0
        activePos = -1

        # add all configurations we have, remember the index of the active one
        for conf in self.configs:
            ## print(repr(conf))
            model.append([conf[0], str(pos)])
            if (conf[0] == self.configname):
                activePos = pos
            pos = pos + 1
        combo.set_model(model)
        # let the comboBox show the active config entry
        if (activePos != -1):
            combo.set_active(activePos)

    # Callback to select a different config file for editing.
    def comboConfig_changed(self, widget, data=None):

        # get the widget
        combo = self.wTree.get_object("comboConfig")
        model = combo.get_model()
        name = combo.get_active_text()

        # only continue if this is different to the former config
        if (name != self.configname):
            newconf = None

            # let's find the new ConfigObj
            for conf in self.configs:
                if (name == conf[0]):
                    newconf = conf

            # if found set it as our active one and show it's settings in the GUI
            if (newconf != None):
                self.config = newconf[1]
                self.configname = newconf[0]
                self.proxi = newconf[2]
                self.readSettings()

    # Callback to create a new config file for editing.
    def btnNew_clicked(self, widget, data=None):
        # reset the entry widget
        self.wTree.get_object("entryNewName").set_text('')
        self.windowNew.show()

    # Callback to delete a config file.
    def btnDelete_clicked(self, widget, data=None):

        # never delete the last config
        if len(self.configs) == 1:
            dlg = gtk.MessageDialog(None, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK,
                                    _("The last configuration file cannot be deleted."))
            dlg.run()
            dlg.destroy()
            return 0

        # security question
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_YES_NO,
                                _("Do you really want to delete the configuration '%s'.") % self.configname)
        retval = dlg.run()
        dlg.destroy()
        if retval == gtk.RESPONSE_YES:

            # ok, now stop the detection for that config
            self.proxi.Stop = True

            # save the filename
            configfile = self.config.filename

            # rip it out of our configs array
            self.configs.remove([self.configname, self.config, self.proxi])

            # change active config to the next one
            self.configs.sort()
            self.configname = configs[0][0]
            self.config = configs[0][1]
            self.proxi = configs[0][2]

            # update gui
            self.readSettings()
            self.fillConfigCombo()

            # now delete the file on the disk
            try:
                os.remove(configfile)
            except:

                # should this be a GUI message?
                print(_("The configfile '%s' could not be deleted.") % configfile)

    # Callback to rename a config file.
    def btnRename_clicked(self, widget, data=None):

        # set the entry widget
        self.wTree.get_object("entryRenameName").set_text(self.configname)
        self.windowRename.show()

    # Callback to show the pop-up menu if icon is right-clicked.
    def popupMenu(self, widget, button, event_time, data=None):
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, None, 3, button, event_time)
        pass

    # Callback to show and hide the config dialog.
    def showWindow(self, widget, data=None, event_time=None):
        # params = "params are:\nself:{0}\nwidget:{1}\ndata:{2}\nevent_time:{3}"
        # params = params.format(self, widget, data, event_time)
        # print(repr(params))
        if self.window.get_property("visible"):
            self.Close()
        else:
            self.window.show()
            for config in self.configs:
                config[2].Simulate = True

    # Callback to create and show the info dialog.
    def aboutPressed(self, widget, data=None):
        logo = GdkPixbuf.Pixbuf.new_from_file(dist_path + icon_base)
        description = _("Leave it - it's locked, come back - it's back too...")
        blueproximity_copyright = u"""Copyright (c) 2007,2008 Lars Friedrichs"""
        people = [
            u"Lars Friedrichs <LarsFriedrichs@gmx.de>",
            u"Tobias Jakobs",
            u"Zsolt Mazolt",
            u"Rodrigo Gambra-Middleton (current fork maintainer) <rodrigo@tiktaalik.dev>"]
        translators = """Translators:
                           de Lars Friedrichs <LarsFriedrichs@gmx.de>
                           en Lars Friedrichs <LarsFriedrichs@gmx.de>
                           es César Palma <cesarpalma80@gmail.com>
                           fa Ali Sattari <ali.sattari@gmail.com>
                           hu Kami <kamihir@freemail.hu>
                           it e633 <e633@users.sourceforge.net>
                           Prosper <prosper.nl@gmail.com>
                           ru Alexey Lubimov
                           sv Jan Braunisch <x@r6.se>
                           th Maythee Anegboonlap & pFz <null@llun.info>
                         Former translators:
                           fr Claude <f5pbl@users.sourceforge.net>
                           sv Alexander Jönsson <tp-sv@listor.tp-sv.se>
                           sv Daniel Nylander <dnylander@users.sourceforge.net>
                                    """
        blueproximity_license = _("""
        BlueProximity is free software; you can redistribute it and/or modify it 
        under the terms of the GNU General Public License as published by the 
        Free Software Foundation; either version 2 of the License, or 
        (at your option) any later version.

        BlueProximity is distributed in the hope that it will be useful, but 
        WITHOUT ANY WARRANTY; without even the implied warranty of 
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
        See the GNU General Public License for more details.

        You should have received a copy of the GNU General Public License 
        along with BlueProximity; if not, write to the 

        Free Software Foundation, Inc., 
        59 Temple Place, Suite 330, 
        Boston, MA  02111-1307  USA
        """)
        about = gtk.AboutDialog()
        about.set_icon(logo)
        about.set_name("BlueProximity")
        about.set_version(SW_VERSION)
        about.set_copyright(blueproximity_copyright)
        about.set_comments(description)
        about.set_authors(people)
        about.set_logo(logo)
        about.set_license(blueproximity_license)
        about.set_website("http://blueproximity.sourceforge.net")
        about.set_translator_credits(translators)
        about.connect('response', lambda widget, response: widget.destroy())
        about.show()

    # Callback to activate and deactivate pause mode.
    # This is actually done by removing the proximity object's mac address.
    def pausePressed(self, widget, data=None):
        if self.pauseMode:
            self.pauseMode = False
            for config in configs:
                config[2].dev_mac = config[2].lastMAC
                config[2].Simulate = False

            from gi.repository import GdkPixbuf
            GdkPixbuf.Pixbuf.new_from_file(dist_path + icon_error)
        else:
            self.pauseMode = True
            for config in configs:
                config[2].lastMAC = config[2].dev_mac
                config[2].dev_mac = ''
                config[2].Simulate = True
                config[2].kill_connection()

    # Helper function to set a ComboBox's value to value if that exists in the Combo's list
    # The value is not changed if the new value is not member of the list.
    # @param widget a gtkComboBox object
    # @param value the value the gtkComboBox should be set to.    
    def setComboValue(self, widget, value):
        model = widget.get_model()
        for row in model:
            if row[0] == value:
                widget.set_active_iter(row.iter)
                break

    # Helper function to get a ComboBox's value
    def getComboValue(self, widget):
        model = widget.get_model()
        iterator = widget.get_active_iter()
        return model.get_value(iterator, 0)

    # Reads the config settings and sets all GUI components accordingly.
    def readSettings(self):

        # Updates the controls to show the actual configuration of the running proximity
        was_live = self.gone_live
        self.gone_live = False
        self.wTree.get_object("entryMAC").set_text(self.config['device_mac'])
        self.wTree.get_object("entryChannel").set_value(int(self.config['device_channel']))
        self.wTree.get_object("hscaleLockDist").set_value(int(self.config['lock_distance']))
        self.wTree.get_object("hscaleLockDur").set_value(int(self.config['lock_duration']))
        self.wTree.get_object("hscaleUnlockDist").set_value(int(self.config['unlock_distance']))
        self.wTree.get_object("hscaleUnlockDur").set_value(int(self.config['unlock_duration']))
        self.wTree.get_object("comboLock").prepend_text(self.config['lock_command'])
        self.wTree.get_object("comboUnlock").prepend_text(self.config['unlock_command'])
        self.wTree.get_object("comboProxi").prepend_text(self.config['proximity_command'])
        self.wTree.get_object("hscaleProxi").set_value(int(self.config['proximity_interval']))
        self.wTree.get_object("checkSyslog").set_active(self.config['log_to_syslog'])
        self.setComboValue(self.wTree.get_object("comboFacility"), self.config['log_syslog_facility'])
        self.wTree.get_object("checkFile").set_active(self.config['log_to_file'])
        self.wTree.get_object("entryFile").set_text(self.config['log_filelog_filename'])
        self.gone_live = was_live

    # Reads the current settings from the GUI and stores them in the configobj object.
    def writeSettings(self):

        # Updates the running proximity and the config file with the new settings from the controls
        was_live = self.gone_live
        self.gone_live = False
        self.proxi.dev_mac = self.wTree.get_object("entryMAC").get_text()
        self.proxi.dev_channel = int(self.wTree.get_object("entryChannel").get_value())
        self.proxi.gone_limit = -self.wTree.get_object("hscaleLockDist").get_value()
        self.proxi.gone_duration = self.wTree.get_object("hscaleLockDur").get_value()
        self.proxi.active_limit = -self.wTree.get_object("hscaleUnlockDist").get_value()
        self.proxi.active_duration = self.wTree.get_object("hscaleUnlockDur").get_value()
        self.config['device_mac'] = str(self.proxi.dev_mac)
        self.config['device_channel'] = str(self.proxi.dev_channel)
        self.config['lock_distance'] = int(-self.proxi.gone_limit)
        self.config['lock_duration'] = int(self.proxi.gone_duration)
        self.config['unlock_distance'] = int(-self.proxi.active_limit)
        self.config['unlock_duration'] = int(self.proxi.active_duration)
        self.config['lock_command'] = self.wTree.get_object('comboLock').get_active_text()
        self.config['unlock_command'] = str(self.wTree.get_object('comboUnlock').get_active_text())
        self.config['proximity_command'] = str(self.wTree.get_object('comboProxi').get_active_text())
        self.config['proximity_interval'] = int(self.wTree.get_object('hscaleProxi').get_value())
        self.config['log_to_syslog'] = self.wTree.get_object("checkSyslog").get_active()
        self.config['log_syslog_facility'] = str(self.getComboValue(self.wTree.get_object("comboFacility")))
        self.config['log_to_file'] = self.wTree.get_object("checkFile").get_active()
        self.config['log_filelog_filename'] = str(self.wTree.get_object("entryFile").get_text())
        self.proxi.logger.configureFromConfig(self.config)
        self.config.write()
        self.gone_live = was_live

    # Callback for resetting the values for the min/max viewer.
    def btnResetMinMax_clicked(self, widget, data=None):
        self.minDist = -255
        self.maxDist = 0

    # Callback called by almost all GUI elements if their values are changed.
    # We don't react if we are still initializing (self.gone_live==False)
    # because setting the values of the elements would already fire their change events.
    # @see gone_live
    def event_settings_changed(self, widget, data=None):
        if self.gone_live:
            self.writeSettings()
        pass

    # Callback called by certain GUI elements if their values are changed.
    # We don't react if we are still initializing (self.gone_live==False)
    # because setting the values of the elements would already fire their change events.
    # But in any case we kill a possibly existing connection. 
    # Changing the rfcomm channel e.g. fires this event instead of event_settings_changed.
    # @see event_settings_changed
    def event_settings_changed_reconnect(self, widget, data=None):
        self.proxi.kill_connection()
        if self.gone_live:
            self.writeSettings()
        pass

    # Callback called when one clicks into the channel scan results.
    # It sets the 'selected channel' field to the selected channel
    def event_scanChannelResult_changed(self, widget, data=None):

        # Put selected channel in channel entry field
        selection = self.wTree.get_object("treeScanChannelResult").get_selection()
        (model, tree_iter) = selection.get_selected()
        # print("selection.getselected() is: {}".format(repr(selection.get_selected())))
        # print("tree_iter is: {}".format(repr(tree_iter)))
        if tree_iter is not None:
            value = model.get_value(tree_iter, 0)
            self.wTree.get_object("entryChannel").set_value(int(value))
            entry_channel_value = self.wTree.get_object("entryChannel").get_value()
            print('tree_iter is: {0}\n\n'
                  'Also, repr(tree_iter) is: {1}\n\n'
                  'And entryChannel value is: {2}\n\n'.format(tree_iter, repr(tree_iter), entry_channel_value))
            self.writeSettings()

    # Callback to just close and not destroy the main window
    def btnClose_clicked(self, widget, data=None):
        self.Close()
        return 1

    # Callback called when one clicks on the 'use selected address' button
    # it copies the MAC address of the selected device into the mac address field.
    def btnSelect_clicked(self, widget, data=None):

        # Takes the selected entry in the mac/name table and enters its mac in the MAC field
        selection = self.tree.get_selection()
        selection.set_mode(gtk.SelectionMode.SINGLE)
        model, selection_iter = selection.get_selected()
        if (selection_iter):
            mac = self.model.get_value(selection_iter, 0)
            self.wTree.get_widget("entryMAC").set_text(mac)
            self.writeSettings()

    # Callback that is executed when the scan for devices button is clicked
    # actually it starts the scanning asynchronously to have the gui redraw nicely before hanging :-)
    def btnScan_clicked(self, widget, data=None):

        # scan the area for bluetooth devices and show the results
        from gi.repository import Gdk as gdk
        watch = gdk.Cursor(gdk.CursorType.WATCH)
        self.window.get_screen().get_root_window().set_cursor(watch)
        self.model.clear()
        self.model.append(['...', _('Now scanning...')])
        self.setSensitiveConfigManagement(False)
        from gi.repository import GLib as glib
        glib.idle_add(self.cb_btnScan_clicked)

    # Asynchronous callback function to do the actual device discovery scan
    def cb_btnScan_clicked(self):
        tmpMac = self.proxi.dev_mac
        self.proxi.dev_mac = ''
        self.proxi.kill_connection()
        macs = []
        try:
            macs = self.proxi.get_device_list()
        except:
            macs = [['', _('Sorry, the bluetooth device is busy connecting.\n'
                           'Please enter a correct mac address or no address at all\n'
                           'for the config that is not connecting and try again later.')]]
        self.proxi.dev_mac = tmpMac
        self.model.clear()
        for mac in macs:
            self.model.append([mac[0], mac[1]])
        self.window.get_screen().get_root_window().set_cursor(None)
        self.setSensitiveConfigManagement(True)

    # Callback that is executed when the scan channels button is clicked.
    # It starts an asynchronous scan for the channels via initiating a ScanDevice object.
    # That object does the magic, updates the gui and afterwards calls the callback function btnScanChannel_done.
    def btnScanChannel_clicked(self, widget, data=None):

        # scan the selected device for possibly usable channels
        if self.scanningChannels:
            self.wTree.get_object("labelBtnScanChannel").set_label(_("Sca_n channels on device"))
            self.wTree.get_object("channelScanWindow").hide_all()
            self.scanningChannels = False
            self.scanner.doStop()
            self.setSensitiveConfigManagement(True)
        else:
            self.setSensitiveConfigManagement(False)
            mac = self.proxi.dev_mac
            if self.pauseMode:
                mac = self.lastMAC
                was_paused = True
            else:
                self.pausePressed(None)
                was_paused = False
            self.wTree.get_object("labelBtnScanChannel").set_label(_("Stop sca_nning"))
            self.wTree.get_object("channelScanWindow").show_all()
            self.scanningChannels = True
            dialog = gtk.MessageDialog(text=_("The scanning process tries to connect to each of "
                                              "the 30 possible ports. This will take some time and "
                                              "you should watch your bluetooth device for any actions "
                                              "to be taken. If possible click on accept/connect. If you "
                                              "are asked for a pin your device was not paired properly before, "
                                              "see the manual on how to fix this."),
                                       buttons=gtk.ButtonsType.OK)
            dialog.connect("response", lambda x, y: dialog.destroy())
            dialog.run()
            self.scanner = ScanDevice(mac, self.modelScan, was_paused, self.btnScanChannel_done)
        return 0

    # The callback that is called by the ScanDevice object that scans for a device's usable rfcomm channels.
    # It is called after all channels have been scanned.
    # @param was_paused informs this function about the pause state before the scan started.
    # That state will be reconstructed by the function.
    def btnScanChannel_done(self, was_paused):
        self.wTree.get_object("labelBtnScanChannel").set_label(_("Sca_n channels on device"))
        self.scanningChannels = False
        self.setSensitiveConfigManagement(True)
        if not was_paused:
            self.pausePressed(None)
            self.proxi.Simulate = True

    def Close(self):

        # Hide the settings window
        self.window.hide()

        # Disable simulation mode for all configs
        for config in configs:
            config[2].Simulate = False

    def quit(self, widget, data=None):

        # try to close everything correctly
        from gi.repository import GdkPixbuf
        GdkPixbuf.Pixbuf.new_from_file(dist_path + icon_att)
        for config in configs:
            config[2].logger.log_line(_('stopped.'))
            config[2].Stop = 1
            time.sleep(2)
            gtk.main_quit()

    # Updates the GUI (values, icon, tooltip) with the latest values
    # is always called via gobject.timeout_add call to run asynchronously without a seperate thread.
    def updateState(self):

        # update the display with newest measurement values (once per second)
        newVal = int(self.proxi.Dist)  # Values are negative!
        if newVal > self.minDist:
            self.minDist = newVal
        if newVal < self.maxDist:
            self.maxDist = newVal
        self.wTree.get_object("labState").set_text(_("min: ") +
                                                   str(-self.minDist) + _(" max: ") + str(-self.maxDist) + _(
            " state: ") + self.proxi.State)
        self.wTree.get_object("hscaleAct").set_value(-newVal)

        # Update icon too
        if self.pauseMode:
            from gi.repository import GdkPixbuf
            # GdkPixbuf.Pixbuf.new_from_file(dist_path + icon_pause)
            self.icon.set_icon_name(dist_path + icon_pause)
            self.icon.set_tooltip_text(_('Pause Mode - not connected'))
        else:

            # we have to show the 'worst case' since we only have one icon but many configs...
            connection_state = 0
            con_info = ''
            con_icons = [icon_base, icon_att, icon_away, icon_error]
            for config in configs:
                if config[2].ErrorMsg == "No connection found, trying to establish one...":
                    connection_state = 3
                else:
                    if config[2].State != _('active'):
                        if connection_state < 2:
                            connection_state = 2
                    else:
                        if newVal < config[2].active_limit:
                            if connection_state < 1:
                                connection_state = 1
                if con_info != '':
                    con_info = con_info + '\n\n'
                con_info = con_info + config[0] + ': ' + _('Detected Distance: ') + str(-config[2].Dist) + '; ' + _(
                    "Current State: ") + config[2].State + '; ' + _("Status: ") + config[2].ErrorMsg
            if self.proxi.Simulate:
                simu = _('\nSimulation Mode (locking disabled)')
            else:
                simu = ''
            self.icon.set_icon_name(dist_path + con_icons[connection_state])
            self.icon.set_tooltip_text(con_info + '\n' + simu)
        # print("self.proxi.Simulate is: {}".format(self.proxi.Simulate))
        from gi.repository import GLib as glib
        self.timer = glib.timeout_add(1000, self.updateState)

    def proximityCommand(self):
        # This is the proximity command callback called asynchronously as the updateState above
        if self.proxi.State == _('active') and not self.proxi.Simulate:
            ret_val = os.popen(self.config['proximity_command']).readlines()
            from gi.repository import GLib as glib
            self.timer2 = glib.timeout_add(1000 * int(self.config['proximity_interval']), self.proximityCommand)


# This class creates all logging information in the desired form.
# We may log to syslog with a given syslog facility, while the severety is always info.
# We may also log a simple file.
class Logger(object):
    # Constructor does nothing special.
    def __init__(self):
        self.disable_syslogging()
        self.disable_filelogging()

    # helper function to convert a string (given by a ComboBox) to the corresponding
    # syslog module facility constant.
    # @param facility One of the 8 "localX" facilities or "user".
    def getFacilityFromString(self, facility):
        # Returns the correct constant value for the given facility
        log_dict = {
            "local0": syslog.LOG_LOCAL0,
            "local1": syslog.LOG_LOCAL1,
            "local2": syslog.LOG_LOCAL2,
            "local3": syslog.LOG_LOCAL3,
            "local4": syslog.LOG_LOCAL4,
            "local5": syslog.LOG_LOCAL5,
            "local6": syslog.LOG_LOCAL6,
            "local7": syslog.LOG_LOCAL7,
            "user": syslog.LOG_USER
        }
        return log_dict[facility]

    # Activates the logging to the syslog server.
    def enable_syslogging(self, facility):
        self.syslog_facility = self.getFacilityFromString(facility)
        syslog.openlog('blueproximity', syslog.LOG_PID)
        self.syslogging = True

    # Deactivates the logging to the syslog server.
    def disable_syslogging(self):
        self.syslogging = False
        self.syslog_facility = None

    # Activates the logging to the given file.
    # Actually tries to append to that file first, afterwards tries to write to it.
    # If both don't work it gives an error message on stdout and does not activate the logging.
    # @param filename The complete filename where to log to        
    def enable_filelogging(self, filename):
        self.filename = filename
        try:
            # let's append
            self.flog = open(filename, 'a')
            print(self.flog)
            self.filelogging = True
        except:
            try:
                # did not work, then try to create file (is this really needed or does python
                # know another attribute to file()?
                self.flog = open(filename, 'w')
                self.filelogging = True
            except:
                print(_("Could not open logfile '{}' for writing.").format(filename))
                self.disable_filelogging

    # Deactivates logging to a file.
    def disable_filelogging(self):
        try:
            self.flog.close()
        except:
            pass
        self.filelogging = False
        self.filename = ''

    # Outputs a line to the logs. Takes care of where to put the line.
    # @param line A string that is printed in the logs. The string is unparsed and not sanatized by any means.
    def log_line(self, line):
        if self.syslogging:
            syslog.syslog(self.syslog_facility | syslog.LOG_NOTICE, line)
        if self.filelogging:
            try:
                self.flog.write(time.ctime() + " blueproximity: " + line + "\n")
                self.flog.flush()
            except:
                self.disable_filelogging()

    # Activate the logging mechanism that are requested by the given configuration.
    # @param config A ConfigObj object containing the needed settings.
    def configureFromConfig(self, config):
        if config['log_to_syslog']:
            self.enable_syslogging(config['log_syslog_facility'])
        else:
            self.disable_syslogging()
        if config['log_to_file']:
            if self.filelogging and config['log_filelog_filename'] != self.filename:
                self.disable_filelogging()
                self.enable_filelogging(config['log_filelog_filename'])
            elif not self.filelogging:
                self.enable_filelogging(config['log_filelog_filename'])


# ScanDevice is a helper class used for scanning for open rfcomm channels
# on a given device. It uses asynchronous calls via gobject.timeout_add to
# not block the main process. It updates a given model after every scanned port
# and calls a callback function after finishing the scanning process.
class ScanDevice(object):
    # Constructor which sets up and immediately starts the scanning process.
    # Note that the bluetooth device should not be connected while scanning occurs.
    # @param device_mac MAC address of the bluetooth device to be scanned.
    # @param was_paused A parameter to be passed to the finishing callback function.
    # This is to automatically put the GUI in simulation mode if it has been before scanning. (dirty hack)
    # @param callback A callback function to be called after scanning has been done. 
    # It takes one parameter which is preset by the was_paused parameter.
    def __init__(self, device_mac, model, was_paused, callback):
        self.mac = device_mac
        self.model = model
        self.stopIt = False
        self.port = 1
        from gi.repository import GLib as glib
        self.timer = glib.timeout_add(500, self.runStep)
        self.model.clear()
        self.was_paused = was_paused
        self.callback = callback

    # Checks whether a certain port on the given mac address is reachable.
    # @param port An integer from 1 to 30 giving the rfcomm channel number to try to reach.
    # The function does not return True/False but the actual translated strings.
    def scanPortResult(self, port):
        # here we scan exactly one port and give a textual result
        _sock = bluez.btsocket()
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM, _sock)
        try:
            sock.connect((self.mac, port))
            sock.close
            return _("usable")
        except:
            return _("closed or denied")

    # Asynchronous working thread.
    # It scans a single port at a time and reruns with the next one in the next loop.
    def runStep(self):
        # here the scanning of all ports is done
        self.model.append([str(self.port), self.scanPortResult(self.port)])
        self.port = self.port + 1
        if not self.port > 30 and not self.stopIt:
            from gi.repository import GLib as glib
            self.timer = glib.timeout_add(500, self.runStep)
        else:
            self.callback(self.was_paused)

    def doStop(self):
        self.stopIt = True


# This class does 'all the magic' like regular device detection and decision making
# whether a device is known as present or away. Here is where all the bluetooth specific
# part takes place. It is build to be run a a seperate thread and would run perfectly without any GUI.
# Please note that the present-command is issued by the GUI whereas the locking and unlocking
# is called by this class. This is inconsitent and to be changed in a future release.
class Proximity(threading.Thread):
    # Constructor to setup our local variables and initialize threading.
    # @param config a ConfigObj object that stores all our settings
    def __init__(self, config):
        threading.Thread.__init__(self, name="WorkerThread")
        self.config = config
        self.Dist = -255
        self.State = _("gone")
        self.Simulate = False
        self.Stop = False
        self.procid = 0
        self.dev_mac = self.config['device_mac']
        self.dev_channel = self.config['device_channel']
        self.ringbuffer_size = self.config['buffer_size']
        self.ringbuffer = [-254] * self.ringbuffer_size
        self.ringbuffer_pos = 0
        self.gone_duration = self.config['lock_duration']
        self.gone_limit = -self.config['lock_distance']
        self.active_duration = self.config['unlock_duration']
        self.active_limit = -self.config['unlock_distance']
        self.ErrorMsg = _("Initialized...")
        self.sock = None
        self.ignoreFirstTransition = True
        self.logger = Logger()
        self.logger.configureFromConfig(self.config)
        self.timeAct = 0
        self.timeGone = 0
        self.timeProx = 0

    # Returns all active bluetooth devices found. This is a blocking call.
    def get_device_list(self):
        ret_tab = list()
        nearby_devices = bluetooth.discover_devices()
        for bdaddr in nearby_devices:
            ret_tab.append([str(bdaddr), str(bluetooth.lookup_name(bdaddr))])
        return ret_tab

    # Kills the rssi detection connection.
    def kill_connection(self):
        if self.sock != None:
            self.sock.close()
        self.sock = None
        return 0

    # This function is NOT IN USE. It is a try to create a python only way to
    # get the rssi values for a connected device. It does not work at this time.
    def get_proximity_by_mac(self, dev_mac):
        sock = bluez.hci_open_dev(dev_mac)
        old_filter = sock.getsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, 14)

        # perform a device inquiry on bluetooth device #0
        # The inquiry should last 8 * 1.28 = 10.24 seconds
        # before the inquiry is performed, bluez should flush its cache of
        # previously discovered devices
        flt = bluez.hci_filter_new()
        bluez.hci_filter_all_events(flt)
        bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
        sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, flt)

        duration = 4
        max_responses = 255
        cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, duration, max_responses)
        bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, cmd_pkt)

        results = []

        done = False
        while not done:
            pkt = sock.recv(255)
            ptype, event, plen = struct.unpack("BBB", pkt[:3])
            if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
                pkt = pkt[3:]
                nrsp = struct.unpack("B", pkt[0])[0]
                for i in range(nrsp):
                    addr = bluez.ba2str(pkt[1 + 6 * i:1 + 6 * i + 6])
                    rssi = struct.unpack("b", pkt[1 + 13 * nrsp + i])[0]
                    results.append((addr, rssi))
                    print("[%s] RSSI: [%d]" % (addr, rssi))
            elif event == bluez.EVT_INQUIRY_COMPLETE:
                done = True
            elif event == bluez.EVT_CMD_STATUS:
                status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
                if status != 0:
                    print("uh oh...")
                    printpacket(pkt[3:7])
                    done = True
            else:
                print("unrecognized packet type 0x%02x" % ptype)

        # restore old filter
        sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, old_filter)

        sock.close()
        return results

    # Returns the rssi value of a connection to the given mac address.
    # @param dev_mac mac address of the device to check.
    # This should also be removed but I still have to find a way to read the rssi value from python
    def get_proximity_once(self, dev_mac):
        ret_val = os.popen("hcitool rssi " + dev_mac + " 2>/dev/null").readlines()
        if ret_val == []:
            ret_val = -255
        else:
            ret_val = ret_val[0].split(':')[1].strip(' ')
        return int(ret_val)

    # Fire up an rfcomm connection to a certain device on the given channel.
    # Don't forget to set up your phone not to ask for a connection.
    # (at least for this computer.)
    # @param dev_mac mac address of the device to connect to.
    # @param dev_channel rfcomm channel we want to connect to.
    def get_connection(self, dev_mac, dev_channel):
        try:
            self.procid = 1
            _sock = bluez.btsocket()
            self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM, _sock)
            self.sock.connect((dev_mac, dev_channel))
        except:
            self.procid = 0
            pass
        return self.procid

    def run_cycle(self, dev_mac, dev_channel):
        # reads the distance and averages it over the ringbuffer
        self.ringbuffer_pos = (self.ringbuffer_pos + 1) % self.ringbuffer_size
        self.ringbuffer[self.ringbuffer_pos] = self.get_proximity_once(dev_mac)
        ret_val = 0
        for val in self.ringbuffer:
            ret_val = ret_val + val
        if self.ringbuffer[self.ringbuffer_pos] == -255:
            self.ErrorMsg = _("No connection found, trying to establish one...")
            self.kill_connection()
            self.get_connection(dev_mac, dev_channel)
        return int(ret_val / self.ringbuffer_size)

    def go_active(self):
        # The Doctor is in
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is unlocked'))
            if self.timeAct == 0:
                self.timeAct = time.time()
                ret_val = os.popen(self.config['unlock_command']).readlines()
                self.timeAct = 0
            else:
                self.logger.log_line(
                    _('A command for %s has been skipped because the former command did not finish yet.') % _(
                        'unlocking'))
                self.ErrorMsg = _(
                    'A command for %s has been skipped because the former command did not finish yet.') % _('unlocking')

    def go_gone(self):
        # The Doctor is out
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is locked'))
            if self.timeGone == 0:
                self.timeGone = time.time()
                ret_val = os.popen(self.config['lock_command']).readlines()
                self.timeGone = 0
            else:
                self.logger.log_line(
                    _('A command for %s has been skipped because the former command did not finish yet.') % _(
                        'locking'))
                self.ErrorMsg = _(
                    'A command for %s has been skipped because the former command did not finish yet.') % _('locking')

    def go_proximity(self):
        # The Doctor is still in
        if self.timeProx == 0:
            self.timeProx = time.time()
            ret_val = os.popen(self.config['proximity_command']).readlines()
            self.timeProx = 0
        else:
            self.logger.log_line(
                _('A command for %s has been skipped because the former command did not finish yet.') % _('proximity'))
            self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _(
                'proximity')

    # This is the main loop of the proximity detection engine.
    # It checks the rssi value against limits and invokes all commands.
    def run(self):
        duration_count = 0
        state = _("gone")
        proxiCmdCounter = 0
        while not self.Stop:
            # print "tick"
            try:
                if self.dev_mac != "":
                    self.ErrorMsg = _("running...")
                    dist = self.run_cycle(self.dev_mac, self.dev_channel)
                else:
                    dist = -255
                    self.ErrorMsg = "No bluetooth device configured..."
                if state == _("gone"):
                    if dist >= self.active_limit:
                        duration_count = duration_count + 1
                        if duration_count >= self.active_duration:
                            state = _("active")
                            duration_count = 0
                            if not self.Simulate:
                                from gi.repository import GLib as glib
                                # start the process asynchronously so we are not hanging here...
                                timerAct = glib.timeout_add(5, self.go_active)
                                # self.go_active()
                    else:
                        duration_count = 0
                else:
                    if dist <= self.gone_limit:
                        duration_count = duration_count + 1
                        if duration_count >= self.gone_duration:
                            state = _("gone")
                            proxiCmdCounter = 0
                            duration_count = 0
                            if not self.Simulate:
                                # start the process asynchronously so we are not hanging here...
                                from gi.repository import GLib as glib
                                timerGone = glib.timeout_add(5, self.go_gone)
                                # self.go_gone()
                    else:
                        duration_count = 0
                        proxiCmdCounter = proxiCmdCounter + 1
                if dist != self.Dist or state != self.State:
                    # print "Detected distance atm: " + str(dist) + "; state is " + state
                    pass
                self.State = state
                self.Dist = dist
                # let's handle the proximity command
                if (proxiCmdCounter >= int(self.config['proximity_interval'])) and not self.Simulate and (
                        self.config['proximity_command'] != ''):
                    proxiCmdCounter = 0
                    # start the process asynchronously so we are not hanging here...
                    from gi.repository import GLib as glib
                    timerProx = glib.timeout_add(5, self.go_proximity)
                time.sleep(1)
            except KeyboardInterrupt:
                break
        self.kill_connection()


if __name__ == '__main__':
    import gettext

    gettext.bindtextdomain(APP_NAME, local_path)
    gettext.textdomain(APP_NAME)

    # react on ^C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # read config if any
    configs = []
    new_config = True
    conf_dir = os.path.join(os.getenv('HOME'), '.blueproximity')
    try:

        # check if config directory exists
        os.mkdir(conf_dir)
        print(_("Creating new config directory '%s'.") % conf_dir)

        # we should now look for an old config file and try to move it to a better place...
        os.rename(os.path.join(os.getenv('HOME'), '.blueproximityrc'), os.path.join(conf_dir, _("standard") + ".conf"))
        print(_("Moved old configuration to the new config directory."))
    except:

        # we can't create it because it is already there...
        pass

    # now look for .conf files in there
    vdt = Validator()
    for filename in os.listdir(conf_dir):
        if filename.endswith('.conf'):
            try:

                # add every valid .conf file to the array of configs
                config = ConfigObj(os.path.join(conf_dir, filename),
                                   {'create_empty': False, 'file_error': True, 'configspec': conf_specs})

                # first validate it
                config.validate(vdt, copy=True)

                # rewrite it in a secure manner
                config.write()

                # if everything worked add this config as functioning
                configs.append([filename[:-5], config])
                new_config = False
                print(_("Using config file '%s'.") % filename)
            except:
                print(_("'%s' is not a valid config file.") % filename)

    # no previous configuration could be found so let's create a new one
    if new_config:
        config = ConfigObj(os.path.join(conf_dir, _('standard') + '.conf'),
                           {'create_empty': True, 'file_error': False, 'configspec': conf_specs})

        # next line fixes a problem with creating empty strings in default values for configobj
        config['device_mac'] = ''
        config.validate(vdt, copy=True)

        # write it in a secure manner
        config.write()
        configs.append([_('standard'), config])

        # we can't log these messages since logging is not yet configured, so we just print it to stdout
        print(_("Creating new configuration."))
        print(_("Using config file '%s'.") % _('standard'))

    # now start the proximity detection for each configuration
    for config in configs:
        p = Proximity(config[1])
        p.start()
        config.append(p)

    configs.sort()

    # the idea behind 'configs' is an array containing the name, the configobj and the proximity object
    pGui = ProximityGUI(configs, new_config)

    # make GTK threadable
    ## from gi.repository import Gdk as gdk
    ## gdk.threads_init()

    # aaaaand action!
    gtk.main()
