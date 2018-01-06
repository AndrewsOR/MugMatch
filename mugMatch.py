#!/usr/bin/python3

#-------- Required Libraries --------------------------------------
# for API requests                            
import requests
from requests_oauthlib import OAuth1

# for GUI elements
import tkinter as tk           # using several elements, so import whole module
from tkinter import messagebox
#from PIL import ImageTk, Image # from Python Image Library
from PIL import Image, ImageTk 
# for dataset manipulation
import pandas as pd

# this is the credentials.py you created from credentialsTemplate.py
# (or implement your own handshake)
from mugCredentials import API_KEY, API_SECRET, \
                            ACCESS_TOKEN, ACCESS_SECRET, USER_NAME          
#-------------------------------------------------------------------


#-------- API requests ---------------------------------------------
JSON_HEADERS = {'Accept':'application/json','Content-Type':'application/json'} 

def getJsonResponse(url, auth):
    """ wraps GET request and parses JSON response """
    r = requests.get(url, auth = auth, headers = JSON_HEADERS)
    r.raise_for_status()
    return r.json()['Response']   

def deleteJsonResponse(url, auth): 
    """ wraps DELETE request and parses JSON response """
    r =  requests.delete(url, auth = auth, headers = JSON_HEADERS)
    r.raise_for_status()
    return r.json()['Response']  
    
def getAlbumsForUser( userName, 
                      auth, 
                      albumAttribs = ['AlbumKey','Name','ImageCount']
                     ):
    """ 
    Given a user name, return (in a list) dicts of attributes of each album. 
    Paginate the request if necessary using the default results count.   
    """
    albumUrl  = 'https://api.smugmug.com/api/v2/user/' + userName + '!albums' 
    albumList = []    
    lastPage  = False
    while(not lastPage):
        printNow('Requesting: ' + albumUrl)
        r = getJsonResponse(albumUrl, auth)  
        albumList += [{k:x[k] for k in albumAttribs} for x in r['Album']]
        if 'NextPage' in r['Pages']:
            albumUrl = 'https://api.smugmug.com' + r['Pages']['NextPage']
        else:
            lastPage = True
    return albumList

def getImagesForAlbum( albumKey, 
                       auth, 
                       imageAttribs = ['ImageKey','ArchivedMD5','ArchivedSize',
                                       'FileName','Date','LastUpdated',
                                       'ThumbnailUrl','Uri']
                       ):
    """
    Given an album key, return (in a list) dicts of attributes of each image.
    Include the parent AlbumKey as an attribute.
    Paginate the request if necessary using the default results count.
    """
    albumImagesUrl = 'https://api.smugmug.com/api/v2/album/' + albumKey + '!images'
    imagesList = []
    lastPage = False
    while(not lastPage):
        printNow('Requesting: ' + albumImagesUrl)
        r = getJsonResponse(albumImagesUrl, auth)
        if not 'AlbumImage' in r:
            printNow('Empty album at ' + albumImagesUrl)
        else:
            imagesList += [ {**{k:x[k] for k in imageAttribs},
                                **{'AlbumKey':albumKey} } for x in r['AlbumImage'] ] 
        if 'NextPage' in r['Pages']:
            albumImagesUrl = 'https://api.smugmug.com' + r['Pages']['NextPage']
        else:
            lastPage = True
    return imagesList

def deleteImageFromAlbum( albumImageUri, auth):
    """ Delete an image, given its location in an album"""
    albumImageUrl = 'https://api.smugmug.com' + albumImageUri
    printNow('Deleting: ' + albumImageUrl)
    return deleteJsonResponse(albumImageUrl, auth=auth)

def getAlbumsAndImagesForUser(userName, auth):
    """
    Given a user name, return datasets (as pandas.DataFrame) of: 
        (1) Albums and their attributes
        (2) Images (from any album) and their attributes, including parent album key.
    """
    albums = getAlbumsForUser(userName, auth)
    images = [getImagesForAlbum(x,auth) for x in [a['AlbumKey'] for a in albums]] # nested list
    imageList = [image for album in images for image in album] # flatten the above list
    albumData = pd.DataFrame.from_records(albums).set_index('AlbumKey')
    imageData = pd.DataFrame.from_records(imageList)
    for col in ['LastUpdated','Date']:
        if col in imageData:
            imageData[col] = pd.to_datetime(imageData[col])
    return albumData, imageData   
#------------------------------------------------------------

#----- Data manipulation ------------------------------------
def findDupesAcrossAlbums(albumDf, imageDf):
    """
    Identify duplicate hashes in a given user's albums 
    Return dict of image metadata for each set of duplicates
    """
    # create a dictionary of DataFrames of image metadata, one for each unique image
    imageDf['duplicateHashFlag'] = imageDf.duplicated(subset='ArchivedMD5', keep=False)
    imageDf['fileNameLength'] = imageDf['FileName'].apply(len)
    dupesDf = imageDf.loc[imageDf['duplicateHashFlag']
                            ].join(albumDf.rename(index=str,columns={'Name':'AlbumName'}),
                                   on='AlbumKey').sort_values(['ImageCount','fileNameLength'])
    dupesDf['fileAlbmStr'] = ( dupesDf['AlbumName'].apply(fixStringLength,n=22) +
                              dupesDf['ImageCount'].apply(lambda x: ' ({:>4d} photos)'.format(x)) )
    dupesDf['filePrefStr'] = dupesDf['FileName'].apply(lambda x: fixStringLength(x.split('.')[0],n=14, alignRight=False) )
    dupesDf['fileSuffStr'] = dupesDf['FileName'].apply(lambda x: x.split('.')[-1].lower())                       
    dupesDf['fileSizeStr'] = (dupesDf['ArchivedSize'] / 1024**2).round(2).apply(lambda x: '{:.2f}M'.format(x))
    dupesDf['ImageDesc'] = (  dupesDf['fileAlbmStr'] + ' / ' + 
                              dupesDf['filePrefStr'] + ' (' + 
                              dupesDf['fileSizeStr'] + ' ' +  
                              dupesDf['fileSuffStr'] + ')' )            
    return dict( iter( dupesDf[['ArchivedMD5','ThumbnailUrl',
                                'Uri','ImageDesc']].groupby('ArchivedMD5') ) )
#------------------------------------------------------------
    

#------ Misc ------------------------------------------------
def fixStringLength(s, n, ctd='...', alignRight = True):
    """
    Forces a string into a space of size `n`, using continuation
    character `ctd` to indicate truncation
    """
    try: 
       return ( s[:(n-len(ctd))] + ctd if len(s) > n 
                  else s.rjust(n) if alignRight 
                  else s.ljust(n)   
               )   
    except (AttributeError, TypeError, ValueError):
       raise AssertionError('Input should be a string')
       
def printNow(x): 
    """Shorthand for printing to console"""
    print(x, flush=True)       
#------------------------------------------------------------


#---- GUI ---------------------------------------------------
class CopyDeleter(tk.Frame):
    def __init__(self, root, data, auth):
        """
        Scrollbar code credit to Bryan Oakley:
        https://stackoverflow.com/a/3092341/2573061
        """
        super().__init__()     
        self.canvas = tk.Canvas(root, borderwidth=0)
        self.frame  = tk.Frame(self.canvas)
        self.scroll = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4,4), window=self.frame, anchor="nw", 
                                  tags="self.frame")
        self.frame.bind("<Configure>", self.onFrameConfigure)
        self.data = data
        self.auth = auth
        self.initUI() 
            
    def onFrameConfigure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def initUI(self):
        """
        Creates the static UI content and the innerFrame that will hold the
        dynamic UI content (i.e., the Checkbuttons for the copies)
        """
        self.master.title("Duplicate Removal")
        self.instructLabel = tk.Label( self.frame, justify='left',
                                      text = "Select the copies you wish to DELETE.")
        self.skipButton   = tk.Button( self.frame, text="Skip", command = self.populateUI)
        self.deleteButton = tk.Button( self.frame, text="Delete selected", fg = 'red',
                                       command = self.executeSelection )
        self.quitButton   = tk.Button( self.frame, text="Exit", command=self.frame.quit)
        self.innerFrame   = tk.Frame( self.frame)
        self.instructLabel.pack(anchor = 'nw', padx=5,pady=5)
        self.innerFrame.pack(anchor='nw', padx=5, pady=20, expand=True)
        self.deleteButton.pack(side='left', padx=5,pady=5)
        self.skipButton.pack(side='left', padx=5,pady=5)
        self.quitButton.pack(side='left', padx=5,pady=5)
        self.populateUI()
        
    def clearUI(self):
        """remove any Checkbuttons from previous calls"""
        for child in self.innerFrame.winfo_children(): 
            child.destroy()
    
    def getNextDupeSet(self):
        try:
            return self.data.popitem()[1]
        except KeyError:
            messagebox.showinfo("All done", "You've reviewed all duplicates.")
            raise KeyError()
            
    def populateUI(self):
        """
        Creates and packs a list of Checkbuttons (cbList) into the innerFrame
        By default, the first Checkbutton will be unchecked, all others checked.
        You should help the user out by passing the copy most likely to be the "original"
        (using some business rule) at the head of the list
        """
        self.clearUI()
        try:
            imgData = self.getNextDupeSet() 
            # create lists from data to populate Checkbuttons    
            imgDescs = imgData['ImageDesc'].tolist()
            thumbUrls =  imgData['ThumbnailUrl'].tolist()
            # This reference is required to prevent premature garbage collection
            # More info at the getImgFromUrl docstring
            self.thumbImgs = [self.getImgFromUrl(x) for x in thumbUrls] 
            n = len(imgData.index)    
            self.cbList = [None] * n
            self.cbValues = [tk.BooleanVar() for i in range(n)]
            self.cbDestUris = imgData['Uri'].tolist()
            for i in range(n):
                self.cbList[i] = tk.Checkbutton( self.innerFrame, 
                                            text=imgDescs[i], 
                                            image = self.thumbImgs[i], 
                                            variable = self.cbValues[i],
                                            compound='left' )
                # By default, leave initial button unchecked, others checked
                if i: self.cbList[i].select() 
                self.cbList[i].pack(anchor = 'w', padx=5,pady=5) 
        except KeyError:
            self.frame.quit()  
            
    def getImgFromUrl(self, url): 
        """
        Return an image from a given URL as a Python Image Library PhotoImage
        Uses solution from : https://stackoverflow.com/a/18369957/2573061
        This function is used to grab thumbnails for the photo picker
        It is inside the CopyDeleter class due to tkinter garbage collection problem.
        This problem is described at:
            https://stackoverflow.com/a/3366046/2573061 and:
            http://effbot.org/pyfaq/why-do-my-tkinter-images-not-appear.htm    
        """
        print('Requesting: '+url)
        try:
            r = requests.get(url, auth=self.auth, stream=True)
            pilImg = Image.open(r.raw)
            phoImg = ImageTk.PhotoImage(pilImg)
            return phoImg
        except Exception as e:
           print('Error ' + repr(e) )
           return None
                 
    def querySelection(self):
        return [x.get() for x in self.cbValues]
    
    def getDestUris(self):
        return self.cbDestUris
        
    def executeSelection(self):
        selects = self.querySelection()
        destUris = self.getDestUris()
        if ( not all(x for x in selects) or 
             messagebox.askokcancel(message='Delete ALL occurrences of this image?') 
           ):       
            for selected, destUri in zip(selects,destUris):
                if selected:
                    printNow('Deleting copy at: ' + destUri)
                    deleteImageFromAlbum(destUri, auth=self.auth)
                else:    
                    printNow('Ignoring copy at: ' + destUri)
            self.populateUI()          

#------------------------------------------------------------


def main():
    
    # Authentication (stored locally for now)
    auth = OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)   
    
    # Query all albums for user, then all images in those albums
    albums, images = getAlbumsAndImagesForUser(USER_NAME, auth)
    
    # Find duplicate images across albums using the image hash        
    dupesDict = findDupesAcrossAlbums(albums, images)
    
    # launch the CopyDeleter app
    root = tk.Tk()   
    root.geometry("800x500+250+100") # width x height + xOffset + yOffset 
    app = CopyDeleter(root, data=dupesDict, auth=auth)
    app.mainloop()
    
    # in case you're running it inside an IDE (not recommended):
    try:
        root.destroy()
    except tk.TclError:
        pass 


if __name__ == '__main__':
    main()   