# -*- coding: utf-8 -*-
# Order Favourites program add-on for Kodi 17.6+.
# Lets you see and reorder your Kodi favourites, to organize them.
# In other words, this is an add-on to visually edit your
# favourites.xml file.
#
# doko-desuka 2023
# ====================================================================
import re
import sys
import json
import traceback
try:
    # Python 2.x
    from HTMLParser import HTMLParser
    PARSER = HTMLParser()
    DECODE_STRING = lambda val: val.decode('utf-8')
except ImportError as e:
    # Python 3.4+ (see https://stackoverflow.com/a/2360639)
    import html
    PARSER = html
    DECODE_STRING = lambda val: val # Pass-through.

import xbmc, xbmcgui, xbmcplugin, xbmcvfs
from xbmcaddon import Addon


FAVOURITES_PATH = 'special://userdata/favourites.xml'
THUMBNAILS_PATH_FORMAT = 'special://thumbnails/{folder}/{file}'

PROPERTY_FAVOURITES_RESULT = 'ordfav.result'

ADDON = Addon()
PLUGIN_ID = int(sys.argv[1])
PLUGIN_URL = sys.argv[0]


# Custom Favourites window class for managing the favourites items.
class CustomFavouritesDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

        # Map control IDs to custom handler methods. You can find the control IDs inside
        # the custom skin XML bundled with this add-on (/resources/skins/Default/1080i/CustomFavouritesDialog.XML).
        self.idHandlerDict = {
            101: self.doSelect,
            301: self.close,
            302: self.doReload,
        }

        # Map action IDs to custom handler methods. See more action IDs in
        # https://github.com/xbmc/xbmc/blob/master/xbmc/input/actions/ActionIDs.h
        self.actionHandlerDict = {
            # All click/select actions are already handled by 'idHandlerDict' above.
            #7: self.doSelect, # ACTION_SELECT_ITEM
            #100: self.doSelect, # ACTION_MOUSE_LEFT_CLICK
            #108: self.doSelect, # ACTION_MOUSE_LONG_CLICK
            9: self.doUnselectClose, # ACTION_PARENT_DIR
            92: self.doUnselectClose, # ACTION_NAV_BACK
            10: self.doUnselectClose, # ACTION_PREVIOUS_MENU
            101: self.doUnselectClose, # ACTION_MOUSE_RIGHT_CLICK
            110: self.doUnselectClose # ACTION_BACKSPACE
        }
        self.noop = lambda: None


    @staticmethod
    def _makeFavourites(favouritesGen):
        LISTITEM = xbmcgui.ListItem
        artDict = {'thumb': None}
        for index, data in enumerate(favouritesGen):
            # The path of each ListItem contains the original favourite entry XML text (with the label, thumb and URL)
            # and this is what's written to the favourites file upon saving -- what changes is the order of the items.
            li = LISTITEM(data[0], path=data[2])
            artDict['thumb'] = data[1] # Slightly faster than recreating a dict on every item.
            li.setArt(artDict)
            li.setProperty('index', str(index)) # To help with resetting, if necessary.
            yield li


    # Function used to start the dialog.
    def doCustomModal(self, favouritesGen):
        self.allItems = list(self._makeFavourites(favouritesGen))
        self.indexFrom = None # Integer index of the source item (or None when nothing is selected).
        self.isDirty = False # Bool saying if there were any user-made changes at all.

        self.doModal()
        if self.isDirty:
            return self._makeResult()
        else:
            return ''


    # Automatically called before the dialog is shown. The UI controls exist now.
    def onInit(self):
        self.panel = self.getControl(101)
        self.panel.reset()
        self.panel.addItems(self.allItems)
        self.setFocusId(100) # Focus the group containing the panel, not the panel itself.


    def onClick(self, controlId):
        self.idHandlerDict.get(controlId, self.noop)()


    def onAction(self, action):
        self.actionHandlerDict.get(action.getId(), self.noop)()


    def doSelect(self):
        selectedPosition = self.panel.getSelectedPosition()
        if self.indexFrom == None:
            # Selecting a new item to reorder.
            self.indexFrom = selectedPosition
            self.panel.getSelectedItem().setProperty('selected', '1')
        else:
            # Something was already selected, so do the reodering.
            if self.indexFrom != selectedPosition:
                # OLD METHOD:
                # Reorder using the .pop() and .insert() methods of the 'self.allItems' list.
                #itemFrom = self.allItems.pop(self.indexFrom)
                #self.allItems.insert(selectedPosition, itemFrom)

                # NEW METHOD:
                # Swap item A and item B.
                self.allItems[self.indexFrom], self.allItems[selectedPosition] = (
                    self.allItems[selectedPosition], self.allItems[self.indexFrom]
                )

                # Reset the selection state.
                self.isDirty = True
                self.indexFrom = None
                self.allItems[selectedPosition].setProperty('selected', '')

                # Commit the changes to the UI.
                self.panel.reset()
                self.panel.addItems(self.allItems)
                self.panel.selectItem(selectedPosition)
            else: # User reselected the item, so just unmark it.
                self.indexFrom = None
                self.panel.getSelectedItem().setProperty('selected', '')


    def doUnselectClose(self):
        # If there's something selected, unselect it. Otherwise, close the dialog.
        if self.indexFrom != None:
            self.allItems[self.indexFrom].setProperty('selected', '')
            self.indexFrom = None
        else:
            self.close()


    def doReload(self):
        if xbmcgui.Dialog().yesno(
            'Order Favourites',
            'This will restore the order from the favourites file so you can try reordering again.\nProceed?'
        ):
            # Re-sort all items based on their original indices.
            selectedPosition = self.panel.getSelectedPosition()
            self.indexFrom = None
            self.allItems = sorted(self.allItems, key=lambda li: int(li.getProperty('index')))
            self.panel.reset()
            self.panel.addItems(self.allItems)
            if selectedPosition != -1:
                self.panel.selectItem(selectedPosition)


    def _makeResult(self):
        INDENT_STRING = ' ' * 4
        return '<favourites>\n' + '\n'.join((INDENT_STRING + li.getPath()) for li in self.allItems) + '\n</favourites>\n'


def favouritesDataGen():
    file = xbmcvfs.File(FAVOURITES_PATH)
    contents = DECODE_STRING(file.read())
    file.close()

    namePattern = re.compile('name\s*=\s*"([^"]+)')
    thumbPattern = re.compile('thumb\s*=\s*"([^"]+)')

    for entryMatch in re.finditer('(<favourite\s+[^<]+</favourite>)', contents):
        entry = entryMatch.group(1)

        match = namePattern.search(entry)
        name = PARSER.unescape(match.group(1)) if match else ''

        match = thumbPattern.search(entry)
        if match:
            thumb = PARSER.unescape(match.group(1))
            cacheFilename = xbmc.getCacheThumbName(thumb)
            if 'ffffffff' not in cacheFilename:
                if '.jpg' in thumb:
                    cacheFilename = cacheFilename.replace('.tbn', '.jpg', 1)
                if '.png' in thumb:
                    cacheFilename = cacheFilename.replace('.tbn', '.png', 1)
                thumb = THUMBNAILS_PATH_FORMAT.format(folder=cacheFilename[0], file=cacheFilename)
        else:
            thumb = ''

        # Yield a 3-tuple of name, thumb-url and the original content of the favourites entry.
        yield name, thumb, entry


def saveFavourites(xmlText):
    if not xmlText:
        return False
    try:
        file = xbmcvfs.File(FAVOURITES_PATH, 'w')
        file.write(xmlText)
        file.close()
    except Exception as e:
        raise Exception('ERROR: unable to write to the Favourites file. Nothing was saved.')
    return True


def getRawWindowProperty(prop):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    return window.getProperty(prop)


def setRawWindowProperty(prop, data):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    window.setProperty(prop, data)


def clearWindowProperty(prop):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    window.clearProperty(prop)


# Debugging helper. Logs a LOGNOTICE-level message.
def xbmcLog(*args):
    xbmc.log('ORDER FAVOURITES > ' + ' '.join((var if isinstance(var, str) else repr(var)) for var in args), xbmc.LOGNOTICE)

#===================================================================================

### Entry point ###

if '/dialog' in PLUGIN_URL:
    ui = CustomFavouritesDialog('CustomFavouritesDialog.xml', ADDON.getAddonInfo('path'), 'Default', '1080i')
    try:
        result = ui.doCustomModal(favouritesDataGen())
        setRawWindowProperty(PROPERTY_FAVOURITES_RESULT, result)
    except Exception as e:
        xbmcLog(traceback.format_exc())
        xbmcgui.Dialog().ok('Order Favourites Error', 'ERROR: "%s"\n(Please check the log for more info)' % str(e))
        clearWindowProperty(PROPERTY_FAVOURITES_RESULT)
    finally:
        del ui # Delete the dialog instance after it's done, as it's not garbage collected.

elif '/save_reload' in PLUGIN_URL:
    # Reload the current profile (which causes a reload of 'favourites.xml').
    try:
        if saveFavourites(getRawWindowProperty(PROPERTY_FAVOURITES_RESULT)):
            clearWindowProperty(PROPERTY_FAVOURITES_RESULT)
            xbmcgui.Dialog().ok('Order Favourites', 'Save successful, press OK to reload your profile...')
            xbmc.executebuiltin('LoadProfile(%s)' % xbmc.getInfoLabel('System.ProfileName'))
            # Alternative way of issuing a profile reload, using JSON-RPC:
            #rpcQuery = (
            #    '{"jsonrpc": "2.0", "id": "1", "method": "Profiles.LoadProfile", "params": {"profile": "%s"}}'
            #    % xbmc.getInfoLabel('System.ProfileName')
            #)
            #xbmc.executeJSONRPC(rpcQuery)
        else:
            # Nothing to save, so just "exit" (go back from) the add-on.
            xbmc.executebuiltin('Action(Back)')
    except Exception as e:
        xbmcLog(traceback.format_exc())
        xbmcgui.Dialog().ok('Order Favourites Error', 'ERROR: "%s"\n(Please check the log for more info)' % str(e))

elif '/save_exit' in PLUGIN_URL:
    # Reload the current profile (which causes a reload of 'favourites.xml').
    try:
        if saveFavourites(getRawWindowProperty(PROPERTY_FAVOURITES_RESULT)):
            clearWindowProperty(PROPERTY_FAVOURITES_RESULT)
            xbmcgui.Dialog().ok('Order Favourites', 'Save successful. Press OK to end the add-on...')
        xbmc.executebuiltin('Action(Back)')
    except Exception as e:
        xbmcLog(traceback.format_exc())
        xbmcgui.Dialog().ok('Order Favourites Error', 'ERROR: "%s"\n(Please check the log for more info)' % str(e))

elif '/exit_only' in PLUGIN_URL:
    # Clear the results property and go back one screen (to wherever the user came from).
    clearWindowProperty(PROPERTY_FAVOURITES_RESULT)
    xbmc.executebuiltin('Action(Back)')
    # Alternative action, going to the Home screen.
    #xbmc.executebuiltin('ActivateWindow(home)') # ID taken from https://kodi.wiki/view/Window_IDs

else:
    # Create the menu items.
    xbmcplugin.setContent(PLUGIN_ID, 'files')

    dialogItem = xbmcgui.ListItem('[COLOR lavender][B]Order favourites...[/B][/COLOR]')
    dialogItem.setArt({'thumb': 'DefaultAddonContextItem.png'})
    dialogItem.setInfo('video', {'plot': 'Open the dialog where you can order your favourites.[CR][B]How to ' \
                                 'use:[/B] select one item, then select another to swap their place. ' \
                                 'Do this as much as needed. Finally, close the dialog and use the menus ' \
                                 'below to save your changes.'})
    saveReloadItem = xbmcgui.ListItem('[COLOR lavender][B]Save and Reload[/B][/COLOR]')
    saveReloadItem.setArt({'thumb': 'DefaultAddonsUpdates.png'})
    saveReloadItem.setInfo('video', {'plot': 'Save any changes you made and reload your Kodi profile '
                                       'to make the changes visible right now, without having to restart Kodi.'})
    saveExitItem = xbmcgui.ListItem('[COLOR lavender][B]Save and exit[/B][/COLOR]')
    saveExitItem.setArt({'thumb': 'DefaultFolderBack.png'})
    saveExitItem.setInfo('video', {'plot': 'Save any changes you made and exit the add-on. [B]Note:[/B] if you '
                                   'make any changes to your favourites using the Favourites screen (like adding, '
                                   'removing or reordering items) before closing Kodi, your changes from this '
                                   'add-on will be forgotten.'})
    exitItem = xbmcgui.ListItem('[COLOR lavender][B]Exit only[/B][/COLOR]')
    exitItem.setArt({'thumb': 'DefaultFolderBack.png'})
    exitItem.setInfo('video', {'plot': 'Exit the add-on (same as pressing Back), without saving your changes.'})
    xbmcplugin.addDirectoryItems(
        PLUGIN_ID,
        (
            # PLUGIN_URL already ends with a slash, so just append the route to it.
            (PLUGIN_URL + 'dialog', dialogItem, False),
            (PLUGIN_URL + 'save_reload', saveReloadItem, False),
            (PLUGIN_URL + 'save_exit', saveExitItem, False),
            (PLUGIN_URL + 'exit_only', exitItem, False)
        )
    )
    xbmcplugin.endOfDirectory(PLUGIN_ID)
