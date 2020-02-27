# -*- coding: utf-8 -*-
# Order Favourites program add-on for Kodi 17.6+.
# Lets you see and reorder your Kodi favourites, to organize them.
#
# doko-desuka 2020
# ====================================================================
import sys
import re
try:
    # Python 2.x
    from HTMLParser import HTMLParser
    PARSER = HTMLParser()
except ImportError:
    # Python 3.4+ (see https://stackoverflow.com/a/2360639)
    import html
    PARSER = html    

import xbmc, xbmcaddon, xbmcgui, xbmcvfs

FAVOURITES_PATH = 'special://userdata/favourites.xml'
THUMBNAILS_PATH_FORMAT = 'special://thumbnails/{folder}/{file}'

# Custom Favourites window class for managing the favourites items.
class CustomFavouritesDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

        # Map control IDs to custom handler methods. You can find the control IDs inside
        # the custom skin XML bundled with this add-on (/resources/skins/Default/1080i/CustomFavouritesDialog.XML).
        self.idHandlerDict = {
            101: self.doSelect,
            301: self.doSave,
            302: self.doReload,
            303: self.doClose
        }

        # Map action IDs to handler custom methods, see more action IDs in
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


    # Function used to start the dialog.
    def doCustomModal(self, favouritesGen, saveHandler):
        allItems = [ ]
        artDict = {'thumb': None}
        for index, data in enumerate(favouritesGen):
            # The path of each ListItem contains the original favourite entry XML text (with the label, thumb and URL)
            # and this is what's written to the favourites file upon saving -- what changes is the order of the items.
            li = xbmcgui.ListItem(data[0], path=data[2])
            artDict['thumb'] = data[1] # Slightly faster than recreating a dict on every item.
            li.setArt(artDict)
            li.setProperty('index', str(index)) # To help with resetting, if necessary.
            allItems.append(li)
            
        self.indexFrom = None # Integer index of the source item (or None when nothing is selected).
        self.allItems = allItems        
        self.saveHandler = saveHandler
        
        self.doModal()


    # Automatically called before the dialog is shown, the UI controls exist now.
    def onInit(self):
        self.panel = self.getControl(101)
        self.panel.reset()
        self.panel.addItems(self.allItems)
        self.setFocusId(100) # Focus the group containing the panel.


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
            # Something was already selected.
            if self.indexFrom != selectedPosition:
                # User selected a different item, so consider the new index as the destination.
                itemFrom = self.allItems.pop(self.indexFrom)
                self.allItems.insert(selectedPosition, itemFrom)     
                
                # Reset the selection state.
                self.indexFrom = None
                itemFrom.setProperty('selected', '')
                
                # Update the panel.
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
            self.doClose()           
            
            
    def doClose(self):
        xbmc.executebuiltin('ActivateWindow(home)') # Return to the Home screen (https://kodi.wiki/view/Window_IDs).
        self.close()
            

    def doReload(self):
        if xbmcgui.Dialog().yesno(
            'Order Favourites',
            'This will undo any of your changes and restore the order from your Favourites file.\nProceed?'
        ):
            # Re-sort all items based on their original indices.
            self.indexFrom = None        
            self.allItems = sorted(self.allItems, key=lambda li: int(li.getProperty('index')))        
            self.panel.reset()        
            self.panel.addItems(self.allItems)        


    def doSave(self):
        if self.saveHandler(self.allItems):
            self.close()
            xbmcgui.Dialog().ok('Order Favourites', 'Save complete. Reloading home screen now...')
            # Reload the current profile (which causes a reload of 'favourites.xml').
            xbmc.executebuiltin('LoadProfile(%s)' % xbmc.getInfoLabel('System.ProfileName'))
        else:
            xbmcgui.Dialog().notification(
                'Order Favourites',
                'Could not save the favourites file',
                xbmcgui.NOTIFICATION_WARNING,
                3000,
                False
            )


def favouritesDataGen():
    file = xbmcvfs.File(FAVOURITES_PATH)
    contents = file.read()
    file.close()

    namePattern = re.compile('name="([^"]+)')
    thumbPattern = re.compile('thumb="([^"]+)')

    for entryMatch in re.finditer('(<favourite\s[^<]+</favourite>)', contents):
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
            
        # Yield a 3-tuple of name, thumb-url and original favourites entry content.
        yield name, thumb, entry


def doSave(allItems):
    # allItems = list of ListItems in the order they should be. Their 'path' holds the XML text of each item.
    INDENT_STRING = ' ' * 4
    xmlText = '<favourites>\n' + '\n'.join((INDENT_STRING + li.getPath()) for li in allItems) + '</favourites>\n'
    try:
        file = xbmcvfs.File(FAVOURITES_PATH, 'w')
        file.write(xmlText)
        file.close()
    except:
        return False
    return True


# Debugging helper. Logs a LOGNOTICE-level message.
def xbmcLog(*args):
    xbmc.log('LOG > ' + ' '.join((var if isinstance(var, str) else repr(var)) for var in args), xbmc.LOGNOTICE)

#===================================================================================

### Entry point ###

ui = CustomFavouritesDialog('CustomFavouritesDialog.xml', xbmcaddon.Addon().getAddonInfo('path'))
ui.doCustomModal(favouritesDataGen(), doSave)
del ui # Delete the dialog instance after it's done, as it's not garbage collected.
