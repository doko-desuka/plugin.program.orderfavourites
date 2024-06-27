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

PROPERTY_FAVOURITES_CONTENTS = 'ordfav.result'
PROPERTY_REARRANGE_MODE = 'ordfav.mode'

# Default arranging mode.
# If you want to change it, comment (add a "#" symbol) at the start of the line
# below and uncomment (remove the "#" symbol) from the line after that.
DEFAULT_MODE = 'Swap'
#DEFAULT_MODE = 'Re-insert'

ADDON = Addon()
PLUGIN_ID = int(sys.argv[1])
PLUGIN_URL = sys.argv[0]

LISTITEM = xbmcgui.ListItem


# Custom Favourites window class for managing the favourites items.
class CustomFavouritesDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

        # Map control IDs to custom handler methods. You can find the control IDs inside
        # the custom skin XML used in this add-on (/resources/skins/Default/1080i/CustomFavouritesDialog.XML).
        self.idHandlerDict = {
            101: self.doSelect,
            301: self.close,
            302: self.doReload,
            303: self.doToggleMode,
            304: self.doHowToUse
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
            110: self.doUnselectClose, # ACTION_BACKSPACE
            117: self.doContextMenu, # ACTION_CONTEXT_MENU
        }
        self.noop = lambda: None

        # See if the default mode has been set up for this Kodi session.
        currentMode = getRawWindowProperty(PROPERTY_REARRANGE_MODE)
        if not currentMode:
            setRawWindowProperty(PROPERTY_REARRANGE_MODE, DEFAULT_MODE)


    # Function used to start the dialog.
    def doCustomModal(self):
        previousContents = getRawWindowProperty(PROPERTY_FAVOURITES_CONTENTS)
        self.allItems = list(self._favouritesItemsGen(favouritesDataGen(previousContents)))
        self.indexFrom = None # Integer index of the source item (or None when nothing is selected).

        self.doModal()
        # As the dialog has closed, store the result (whatever it is) in the memory property.
        setRawWindowProperty(PROPERTY_FAVOURITES_CONTENTS, self._makeResult())


    # Automatically called before the dialog is shown. The UI controls exist now.
    def onInit(self):
        self.panel = self.getControl(101)
        self._refreshPanel()
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
                currentMode = getRawWindowProperty(PROPERTY_REARRANGE_MODE) or 'Swap'
                if currentMode == 'Swap':
                    # Swap item A and item B.
                    self.allItems[self.indexFrom], self.allItems[selectedPosition] = (
                        self.allItems[selectedPosition], self.allItems[self.indexFrom]
                    )
                else:
                    # Reorder using the .pop() and .insert() methods of the 'self.allItems' list.
                    itemFrom = self.allItems.pop(self.indexFrom)
                    # OPTIONAL:
                    # If the source position is more than one step before the target position,
                    # then the target position must be reduced by 1 after popping the source
                    # item, as all positions after the popped item will be reduced.
                    # This causes the source item to always be placed behind the target item
                    # no matter what.
                    #if self.indexFrom < selectedPosition - 1:
                    #    selectedPosition = selectedPosition - 1
                    self.allItems.insert(selectedPosition, itemFrom)

                self.indexFrom = None
                self.allItems[selectedPosition].setProperty('selected', '')

                # Commit the changes to the UI.
                self._refreshPanel(selectedPosition)
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
            'This will restore the order from the favourites file and forget any unsaved changes, '
            'so you can try reordering again.\nProceed?'
        ):
            selectedPosition = self.panel.getSelectedPosition()
            self.indexFrom = None
            # Clear the copy in memory and reload it from file.
            # The favouritesDataGen() generator will also store the file contents
            # it in the memory property.
            clearWindowProperty(PROPERTY_FAVOURITES_CONTENTS)
            self.allItems = list(self._favouritesItemsGen(favouritesDataGen()))
            self._refreshPanel(selectedPosition)
            showInfo('File order restored.')


    def doToggleMode(self):
        currentMode = (getRawWindowProperty(PROPERTY_REARRANGE_MODE)
                       or DEFAULT_MODE)
        toggledMode = 'Re-insert' if currentMode == 'Swap' else 'Swap'
        setRawWindowProperty(PROPERTY_REARRANGE_MODE, toggledMode)


    def doContextMenu(self):
        itemIndex = self.panel.getSelectedPosition()
        if itemIndex > -1:
            item = self.allItems[itemIndex]
            totalItems = len(self.allItems)
            options = (
                LISTITEM('Move to the [B]first[/B] position',
                         'Moves the item to the first position in the grid, pushing '
                         'all other items forward.',
                         offscreen = True),
                LISTITEM('Move to the [B]last[/B] position',
                         'Moves the item to the last position in the grid, pushing back '
                         'any items that were in front of this item.',
                         offscreen = True),
                LISTITEM('Move to position [B]#[/B]...',
                         'Lets you type in the new position to re-insert the item, ranging from '
                         '1 to %d.' % totalItems,
                         offscreen = True),
            )
            heading = 'Item {index} / {total}: "{label}"'.format(label = item.getLabel(),
                                                            index = itemIndex + 1,
                                                            total = totalItems)
            selectedIndex = xbmcgui.Dialog().select(heading, options, useDetails=True)
            if selectedIndex == 0:
                # Pop and move to first position.
                itemFrom = self.allItems.pop(itemIndex)
                self.allItems.insert(0, itemFrom)
                self._refreshPanel(itemIndex)
            elif selectedIndex == 1:
                # Pop and move to last position (AKA append).
                itemFrom = self.allItems.pop(itemIndex)
                self.allItems.append(itemFrom)
                self._refreshPanel(itemIndex)
            elif selectedIndex == 2:
                # Open a dialog to ask the position number. Can be canceled.
                heading = ('Re-insert item ({indexOne} / {total}) at:').format(
                    indexOne = itemIndex + 1,
                    total = totalItems
                )
                result = xbmcgui.Dialog().numeric(0, heading, '')
                if result != '':
                    try:
                        intResult = int(result)
                    except:
                        intResult = -1
                    if intResult < 0 or intResult > totalItems:
                        showInfo('Invalid position (%s), nothing happened' % result, msWait=500)
                    else:
                        itemFrom = self.allItems.pop(itemIndex)
                        self.allItems.insert(intResult - 1, itemFrom)
                        self._refreshPanel(itemIndex)
            else:
                # Do nothing, assume the dialog is canceled (returns an index -1).
                pass
        else:
            showInfo('No item activated', msWait=500)


    def doHowToUse(self):
        xbmcgui.Dialog().textviewer('How to Use',
                                    'There\'s a grid with all of your favourites items. '
                                    'Select one item, and then select another item.[CR][CR]'
                                    '• If the mode is set to [B]Swap[/B] then the two items will '
                                    'swap in place.[CR]'
                                    '• If the mode is set to [B]Re-insert[/B] then the first '
                                    'item will be repositioned at the second item, shifting the '
                                    'second item and any other items in between to fill the empty '
                                    'space.[CR]'
                                    '• You can [B]long-press[/B] / [B]right-click[/B] an item to bring '
                                    'up a menu with more actions.[CR]'
                                    '• In case you selected the wrong item, select it again to '
                                    'unmark it.[CR][CR]'
                                    'Repeat this process to organize your favourites as needed.[CR][CR]'
                                    'When you\'re done, [B]Close[/B] the dialog and then save '
                                    'your changes by selecting either the [B]Save and Reload[/B] '
                                    'or [B]Save and Exit[/B] menus.')


    @staticmethod
    def _favouritesItemsGen(dataGen):
        artDict = {'thumb': None}
        for index, data in enumerate(dataGen):
            # The path of each ListItem contains the original favourite entry XML text (with the label, thumb and URL)
            # and this is what's written to the favourites file upon saving -- what changes is the order of the items.
            li = LISTITEM(data[0], path=data[2])
            artDict['thumb'] = data[1] # Slightly faster than recreating a dict on every item.
            li.setArt(artDict)
            yield li


    def _refreshPanel(self, preselectedPosition=-1):
        self.panel.reset()
        self.panel.addItems(self.allItems)
        if preselectedPosition != -1:
            self.panel.selectItem(preselectedPosition)


    def _makeResult(self):
        INDENT_STRING = ' ' * 4
        return '<favourites>\n' + '\n'.join((INDENT_STRING + li.getPath()) for li in self.allItems) + '\n</favourites>\n'


def favouritesDataGen(contents=None):
    if not contents:
        file = xbmcvfs.File(FAVOURITES_PATH)
        contents = DECODE_STRING(file.read())
        file.close()
        setRawWindowProperty(PROPERTY_FAVOURITES_CONTENTS, contents)

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


# Positional parameters:
#     Stringified and joined with spaces inbetween.
# Keyword arguments:
#     header (title of notification) (optional)
#     msWait (milliseconds that message will last on screen) (optional)
def showInfo(*args, **kwargs):
    header = kwargs.get('header', 'Order Favourites')
    msWait = kwargs.get('msWait', 1000)
    content = ' '.join((var if isinstance(var, str) else repr(var))
                       for var in args if var != '')
    xbmcgui.Dialog().notification(header, content, xbmcgui.NOTIFICATION_INFO,
                                  msWait, False)
    return None


# Debugging helper. Logs a LOGNOTICE-level message.
def xbmcLog(*args):
    xbmc.log('ORDER FAVOURITES > ' + ' '.join((var if isinstance(var, str) else repr(var)) for var in args), xbmc.LOGNOTICE)

#===================================================================================

### Entry point ###

if '/dialog' in PLUGIN_URL:
    ui = CustomFavouritesDialog('CustomFavouritesDialog.xml', ADDON.getAddonInfo('path'), 'Default', '1080i')
    try:
        ui.doCustomModal()
    except Exception as e:
        xbmcLog(traceback.format_exc())
        xbmcgui.Dialog().ok('Order Favourites Error', 'ERROR: "%s"\n(Please check the log for more info)' % str(e))
        clearWindowProperty(PROPERTY_FAVOURITES_CONTENTS)
    finally:
        del ui # Delete the dialog instance after it's done, as it's not garbage collected.

elif '/save_reload' in PLUGIN_URL:
    # Reload the current profile (which causes a reload of 'favourites.xml').
    try:
        if saveFavourites(getRawWindowProperty(PROPERTY_FAVOURITES_CONTENTS)):
            clearWindowProperty(PROPERTY_FAVOURITES_CONTENTS)
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
            showInfo('No changes to save.', msWait=1500)
            xbmc.executebuiltin('Action(Back)')
    except Exception as e:
        xbmcLog(traceback.format_exc())
        xbmcgui.Dialog().ok('Order Favourites Error', 'ERROR: "%s"\n(Please check the log for more info)' % str(e))

elif '/save_exit' in PLUGIN_URL:
    # Reload the current profile (which causes a reload of 'favourites.xml').
    try:
        if saveFavourites(getRawWindowProperty(PROPERTY_FAVOURITES_CONTENTS)):
            clearWindowProperty(PROPERTY_FAVOURITES_CONTENTS)
            xbmcgui.Dialog().ok('Order Favourites', 'Save successful. Press OK to end the add-on...')
        else:
            showInfo('No changes to save.', msWait=1500)
        xbmc.executebuiltin('Action(Back)')
    except Exception as e:
        xbmcLog(traceback.format_exc())
        xbmcgui.Dialog().ok('Order Favourites Error', 'ERROR: "%s"\n(Please check the log for more info)' % str(e))

elif '/exit_only' in PLUGIN_URL:
    # Clear the results property and go back one screen (to wherever the user came from).
    clearWindowProperty(PROPERTY_FAVOURITES_CONTENTS)
    xbmc.executebuiltin('Action(Back)')
    # Alternative action, going to the Home screen.
    #xbmc.executebuiltin('ActivateWindow(home)') # ID taken from https://kodi.wiki/view/Window_IDs

else:
    # Create the menu items.
    xbmcplugin.setContent(PLUGIN_ID, 'files')

    dialogItem = xbmcgui.ListItem('[COLOR lavender][B]Order favourites...[/B][/COLOR]', offscreen=True)
    dialogItem.setArt({'thumb': 'DefaultAddonContextItem.png'})
    dialogItem.setInfo('video', {'plot': 'Open the dialog where you can order your favourites.[CR][CR]'
                                         'There\'s a [B]How to use[/B] button inside with instructions.'})

    aboutItem = xbmcgui.ListItem('[COLOR lavender][B]How to use...[/B][/COLOR]', offscreen=True)
    aboutItem.setArt({'thumb': 'DefaultIconInfo.png'})
    aboutItem.setInfo('video', {'plot': 'Instructions on how to use Order Favourites.'})

    saveReloadItem = xbmcgui.ListItem('[COLOR lavender][B]Save and Reload[/B][/COLOR]', offscreen=True)
    saveReloadItem.setArt({'thumb': 'DefaultAddonsUpdates.png'})
    saveReloadItem.setInfo('video', {'plot': 'Save any changes you made and reload your Kodi profile '
                                       'to make the changes visible right now, without having to restart Kodi.'})

    saveExitItem = xbmcgui.ListItem('[COLOR lavender][B]Save and exit[/B][/COLOR]', offscreen=True)
    saveExitItem.setArt({'thumb': 'DefaultFolderBack.png'})
    saveExitItem.setInfo('video', {'plot': 'Save any changes you made and exit the add-on. [B]Note:[/B] if you '
                                   'make any changes to your favourites using the Favourites screen (like adding, '
                                   'removing or reordering items) before closing Kodi, your changes from this '
                                   'add-on will be forgotten.'})

    exitItem = xbmcgui.ListItem('[COLOR lavender][B]Exit only[/B][/COLOR]', offscreen=True)
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
