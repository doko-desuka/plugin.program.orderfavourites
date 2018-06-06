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
FAVS_PROP = 'swapfavourites.favourites'

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
        li = xbmcgui.ListItem( f['name'] )
        cache = f['cache']
        li.setArt( { 'poster': cache, 'icon': cache } )
      
        if index == indexFrom:
            urlParams = {'from':str(index), 'to':'-1', 'reroute':1}
            li.setLabel( '%s%s%s' % ('[COLOR yellow][B]', li.getLabel(), '[/B][/COLOR]') )
        elif indexFrom != -1:
            urlParams = {'from':str(indexFrom), 'to':str(index), 'swap':1}
        else:
            urlParams = {'from':str(index), 'to':'-1', 'reroute':1}
        url = buildUrl(urlParams)
        listItems.append( (url, li, False) )
    
    liSave = xbmcgui.ListItem('[COLOR greenyellow]SAVE[/COLOR]')
    saveUrl = buildUrl( {'save':1} )
    liSave = (saveUrl, liSave, False)
    listItems.append( liSave )
    
    liReset = xbmcgui.ListItem('[COLOR hotpink]RESET[/COLOR]')
    resetUrl = buildUrl( {'reset':1} )
    liReset = (resetUrl, liReset, False)
    listItems.append( liReset )
    
    # Add dummy items as padding so the grid shows 4 per row like the Favourites screen.
    alignedItems = [ ('', xbmcgui.ListItem(''), False) for n in range(3) ] + listItems

    xbmc.executebuiltin('Container.SetViewMode(500)') # Estuary skin, grid mode.
    xbmcplugin.addDirectoryItems(__handle__, alignedItems)
    xbmcplugin.endOfDirectory(__handle__)


def viewSave():
    global FAVS_PROP
    global FAVOURITES_PATH
    dialog = xbmcgui.Dialog()
    dialog.notification( 'Swap Favourites', 'Saving...', 
    	                    xbmcgui.NOTIFICATION_INFO, 1500, False ) # No sound.
    favs = getWindowProperty(FAVS_PROP)
    if favs:
        builder = ET.TreeBuilder()
        builder.start('favourites', { } )
        for f in favs:
            builder.start('favourite', f['attrib'] )
            builder.data( f['text'] )
            builder.end('favourite')
        builder.end('favourites')
        tree = builder.close()
        file = xbmcvfs.File(FAVOURITES_PATH, 'w')
        treeIndent( tree )
        file.write( ET.tostring(tree, encoding='utf-8') )
        file.close()
        clearWindowProperty(FAVS_PROP)
        xbmc.sleep(200)
        xbmc.executebuiltin('LoadProfile(Master user)') # Reloads 'favourites.xml'.


def viewSwap(params):
    global __handle__
    indexFrom = int( params.get('from', [-1])[0] )
    indexTo = int( params.get('to', [-1])[0] )
    
    if indexFrom != -1 and indexTo != -1:
        global FAVS_PROP
        favs = getWindowProperty(FAVS_PROP)
        if favs:        
            favs[indexFrom], favs[indexTo] = favs[indexTo], favs[indexFrom]
            setWindowProperty(FAVS_PROP, favs)
            
    url = buildUrl( {'indexFrom':'-1'} )
    xbmc.executebuiltin('Container.Update(' + url + ',replace)')


def viewReset():
    favs = loadFavs()
    url = buildUrl( {'from':'-1'} )
    xbmc.executebuiltin('Container.Update( ' + url + ',replace)')


# This is needed to bypass Kodi's URL history behaviour
# since those ListItems are not folders.
def viewReroute(params):
    indexFrom = int( params.get('from', [-1])[0] )
    indexTo = int( params.get('to', [-1])[0] )
    url = buildUrl( {'from':indexFrom, 'to':indexTo} )
    xbmc.executebuiltin('Container.Update( '+ url + ',replace)')
    
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


def loadFavs():
    global FAVOURITES_PATH
    global THUMBNAILS_PATH
    global FAVS_PROP
    file = xbmcvfs.File(FAVOURITES_PATH)
    tree = ET.fromstring(file.read())
    file.close()
    favs = [ ]
    for f in tree.iter('favourite'):
        thumb = f.get('thumb', '')
        cache = xbmc.getCacheThumbName(thumb).replace('.tbn', '.jpg')
        path = THUMBNAILS_PATH + '%s/%s' % (cache[0], cache)
        cache = thumb if ( cache.startswith('ffffffff') or not xbmcvfs.exists(path) ) else path
        favs.append( {'name': f.get('name', ''), 'cache': cache, 'attrib': f.attrib, 'text': f.text } )
    setWindowProperty(FAVS_PROP, favs)
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
elif 'swap' in params:
    viewSwap(params)
elif 'reset' in params:
    viewReset()
elif 'reroute' in params:
    viewReroute(params)
else:
    viewFavourites(params)