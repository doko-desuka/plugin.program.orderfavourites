# -*- coding: utf-8 -*-
import sys
import os
import urlparse, urllib
import json
import xml.etree.ElementTree as ET
import xbmc,xbmcaddon,xbmcgui,xbmcplugin,xbmcvfs

__handle__ = int(sys.argv[1])

FAVOURITES_PATH = xbmc.translatePath('special://userdata/%s' % 'favourites.xml').decode('utf-8')
THUMBNAILS_PATH = xbmc.translatePath('special://thumbnails').decode('utf-8')

FAVS_PROP = 'orderfavourites.favourites'
PAD_PROP = 'orderfavourites.padding'

#===================================================================================		
    
def viewFavourites(params):
    global __handle__
    global FAVS_PROP
    
    if not params:
        params = { }
    indexFrom = int( params.get('from', [-1])[0] )
    indexTo = int( params.get('to', [-1])[0] )
    
    favs = getWindowProperty(FAVS_PROP)
    if not favs:
        favs = loadFavs()
    
    listItems = [ ]
    for index, f in enumerate(favs):
        li = xbmcgui.ListItem( '[COLOR yellow][B]'+f['name']+'[/B][/COLOR]' if index == indexFrom else f['name'] )
        cache = f['cache']
        li.setArt( { 'poster': cache, 'icon': cache } )

        if indexFrom != -1:
            urlParams = {'from': indexFrom, 'to': index, 'insert': 1}
        else:
            urlParams = {'from': index, 'to': -1, 'reroute': 1}
        url = buildUrl(urlParams)
        listItems.append( (url, li, False) )
    
    liSave = xbmcgui.ListItem('[COLOR greenyellow]SAVE[/COLOR]')
    saveUrl = buildUrl( {'save':1} )
    listItems.append( (saveUrl, liSave, False) )
    
    liReset = xbmcgui.ListItem('[COLOR hotpink]RESET[/COLOR]')
    resetUrl = buildUrl( {'reset':1} )
    listItems.append( (resetUrl, liReset, False) )
    
    # Add dummy items as padding so the grid shows 4 per row like the Favourites screen.
    if getWindowProperty(PAD_PROP) > 1:
        alignedItems = [ ('', xbmcgui.ListItem(''), False) for n in range(3) ] + listItems
    else:
        alignedItems = listItems # Custom skins, we can't safely use padding items.

    xbmcplugin.addDirectoryItems(__handle__, alignedItems)
    xbmcplugin.endOfDirectory(__handle__)
    xbmc.executebuiltin('Container.SetViewMode(500)') # Estuary skin, grid mode.
    if indexFrom != -1:
        selectWindowIndex( indexFrom )
    elif indexTo != -1:
        selectWindowIndex( indexTo )


def viewSave():
    global FAVS_PROP
    global FAVOURITES_PATH
    dialog = xbmcgui.Dialog()
    dialog.notification( 'Order Favourites', 'Saving...', 
    	                    xbmcgui.NOTIFICATION_INFO, 1600, False ) # No sound.
    favs = getWindowProperty(FAVS_PROP)
    if favs:
        data = '<favourites>' + ''.join( [ f['original'] for f in favs ] ) + '</favourites>'
        tree = ET.fromstring( data )
        treeIndent( tree )
        file = xbmcvfs.File(FAVOURITES_PATH, 'w')
        file.write( ET.tostring( tree, encoding='utf-8') )
        file.close()
        clearWindowProperty(FAVS_PROP)
        clearWindowProperty(PAD_PROP)
        xbmc.sleep(100) # Just to give the I/O some time.
		profileName = xbmc.getInfoLabel('System.ProfileName')
        xbmc.executebuiltin('LoadProfile(%s)' % profileName) # Reloads 'favourites.xml'.
		

def viewInsert(params):
    indexFrom = int( params.get('from', [-1])[0] )
    indexTo = int( params.get('to', [-1])[0] )
    if indexFrom != -1 and indexTo != -1 and indexFrom != indexTo:
        global FAVS_PROP
        favs = getWindowProperty(FAVS_PROP)
        if favs:
            # New method, reinsert.
            favs.insert( indexTo, favs.pop( indexFrom ) )
            setWindowProperty( FAVS_PROP,  favs )
    url = buildUrl( {'from': -1, 'to': indexTo} ) # 'indexTo' is set so it can be auto-selected.
    xbmc.executebuiltin('Container.Update(%s,replace)' % url)


def viewReset():
    loadFavs()
    url = buildUrl( {'from': -1} )
    xbmc.executebuiltin('Container.Update(%s,replace)' % url)


# This is needed to bypass Kodi's URL history behaviour
# since those ListItems are not folders.
def viewReroute(params):
    indexFrom = params.get('from', [-1])[0]
    indexTo = params.get('to', [-1])[0]
    url = buildUrl( {'from':indexFrom, 'to':indexTo} )
    xbmc.executebuiltin('Container.Update(%s,replace)' % url)
    
#===================================================================================    
    
def buildUrl(query):
    return sys.argv[0] + '?' + urllib.urlencode(query)


def getWindowProperty(prop):
    currentWindow = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    data = currentWindow.getProperty(prop)
    return json.loads(data) if data else { }


def setWindowProperty(prop, data):
    currentWindow = xbmcgui.Window( xbmcgui.getCurrentWindowId())
    temp = json.dumps(data)
    currentWindow.setProperty(prop, temp)
    return temp


def clearWindowProperty(prop):
    currentWindow = xbmcgui.Window( xbmcgui.getCurrentWindowId())
    currentWindow.clearProperty(prop)


def selectWindowIndex( index ):
    currentWindow = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    padding = currentWindow.getProperty(PAD_PROP)
    index += int( padding ) if padding else 0
    cID = currentWindow.getFocusId()
    try:
        currentWindow.getControl(cID).selectItem(index)
    except:
        pass


def loadFavs():
    global FAVOURITES_PATH
    global THUMBNAILS_PATH
    global FAVS_PROP
    global PAD_PROP

    file = xbmcvfs.File(FAVOURITES_PATH)
    tree = ET.fromstring(file.read())
    file.close()
    favs = [ ]
    for f in tree.iter('favourite'):
        thumb = f.get('thumb', '')
        cache = xbmc.getCacheThumbName(thumb).replace('.tbn', '.jpg')
        path = THUMBNAILS_PATH + '%s/%s' % (cache[0], cache)
        cache = thumb if ( cache.startswith('ffffffff') or not xbmcvfs.exists(path) ) else path
        favs.append( {'name': f.get('name', ''), 'cache': cache, 'original': ET.tostring(f, encoding='utf-8')} )
    setWindowProperty(FAVS_PROP, favs)
   
    # Padding, helps with the auto-selection.
    rpcQuery = { 'jsonrpc': '2.0', 'id': '1', 'method': 'Settings.GetSettingValue',
                           'params': {'setting': 'filelists.showparentdiritems'} }
    r = json.loads( xbmc.executeJSONRPC( json.dumps(rpcQuery) ) )
    padding = 1 if r['result'].get('value', False) else 0
    padding += 3 if padding and xbmc.getSkinDir().endswith('estuary') else 0 # For the dummy items we add on Estuary.
    setWindowProperty(PAD_PROP, padding)

    return favs


# From http://effbot.org/zone/element-lib.htm#prettyprint
def treeIndent(elem, level=0):
    i = '\n' + level * '    '
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + '    '
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            treeIndent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

#===================================================================================

### Entry point ###

params = urlparse.parse_qs(sys.argv[2][1:])
if 'save' in params:
    viewSave()
elif 'insert' in params:
    viewInsert(params)
elif 'reset' in params:
    viewReset()
elif 'reroute' in params:
    viewReroute(params)
else:
    viewFavourites(params)