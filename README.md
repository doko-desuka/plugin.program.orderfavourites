# Order Favourites (plugin.program.orderfavourites)
![icon](https://github.com/doko-desuka/plugin.program.orderfavourites/raw/master/icon.png)  
### This is a simple & lightweight program add-on that lets you quickly reorganize your Kodi favourites.  

# How to install:

There are two ways:

A) [From the zips in the Releases page](https://github.com/doko-desuka/plugin.program.orderfavourites/releases).

B) To install from a URL, do this:  
> Go to Settings > File Manager > Add source, use the link https://doko-desuka.github.io/ and give it a name.  
> After that, go to Add-ons > \*Add-ons browser (the open box icon on the top-left, Estuary skin) > Install from zip file > select that named source > see the zips for this add-on for either Leia or Matrix+. Select a zip to install it.  
>  
> \* You can also access the Add-ons browser by going to Settings > Add-ons.

# Main menus & how to use:

While using the add-on, all main menus have descriptions on what they do, and the main dialog has a button titled "How to use..." with instructions on how to use it.

# How to Backup your Favourites File

It's always a good idea to backup your favourites file from time to time so you don't accidentally lose it.  
You can also use this same method to copy other user data from your Kodi profile, like your watched movie/episode databases, add-on settings etc.  
If you have any trouble, try the [official Kodi forums](https://forum.kodi.tv/forumdisplay.php?fid=111) for help.

### Desktop platforms
You can simply go to Kodi's userdata folders ([in these locations](https://kodi.wiki/view/Userdata#Location)) and copy your `favourites.xml` file from there.

### Mobile Platforms (Android, Apple etc)

You need to do it in a few steps, as there are permission issues with accessing an app's files. You do not need to root your device.  
- On Kodi, go to **Settings > File Manager**. The File Manager is a screen with two sides, left and right.
- On the left side, enter the **Profile Directory** folder to find your Kodi userdata files and folders, among which `favourites.xml`.  
- On the right side, go to **Add Source > Browse**, and navigate to some folder of your device that you know you can access. On Android, a good choice is the **Internal Storage/sdcard/Download** folder for example (see asterisk at the bottom), which is visible to all apps. Confirm to add the new source with that location on the right side of the screen and **enter it** so you're viewing the inside of that location.  
- On the left side, **long-press** the `favourites.xml` file and choose **Copy** and confirm, to copy this file to the location being viewed on the right side.  
- From then on you can step outside the Kodi app and use some other app (like a built-in file browser app of your device, or a free app like ZArchiver on Android etc) to move the copied `favourites.xml` from that **sdcard/Download/** location to a USB flash drive or whatever else you had in mind as backup.

\* While USB flash drives might appear as an option in the **Add Source > Browse** dialog, at least on Android there are permission issues preventing Kodi from copying files **directly** to the USB drive (when you try to use the Copy command, it'd fail). That's why a solution that always works is first copying the file(s) to **sdcard/Download/** which is a common folder, and then outside of Kodi accessing that folder and continuing from there, moving your file(s) to some other place.
   
P.S. I consider this add-on feature frozen, I just wanted a quicker way to move Favorite items around. Feel free to fork and modify it, the code is public domain.
