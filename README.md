# MugMatch

### A Python library for SmugMug API v2

My family uses [SmugMug](https://www.smugmug.com/) to store and share photos.  Because we are repeatedly backing up our smartphones, we wind up with a lot of duplicates.  

Although SmugMug has a feature to skip uploading the same filename within the same gallery, it does not check for duplicates across galleries, duplicates already uploaded, or duplicates with different filenames.  

Fortunately, SmugMug [provides](https://news.smugmug.com/introducing-smugmugs-api-2-0-now-in-open-beta-1242ce15e730) an API through which you can obtain a [MD5 checksum](https://en.wikipedia.org/wiki/MD5) for each photo in each album in your account.  You can use this checksum to identify duplicate photos, since it's extremely unlikely that identical checksums will be produced by different photos.

I created a Python library with a GUI that allows me to review each set of duplicates to decide which ones I want to delete.

![Example Screenshot](https://github.com/AndrewsOR/MugMatch/blob/master/ScreenShot.png)

In the course of writing this program, I discovered that about one third of my photos were duplicates, with an average of three copies per duplicate. 

The current defalt selection is to keep the photo in the smallest album, with the smallest filename if there's a tie.

### How to use it

Assuming you already have some photos on a SmugMug account, you can:

1. [Apply](https://api.smugmug.com/api/developer/apply) for a SmugMug API key (accept the API 2.0 beta T&C).  This will give you your `API_KEY` and `API_SECRET`.  If you do this from within your account, the application will be linked to your account.
2. Get the values of `ACCESS_TOKEN` and `ACCESS_SECRET` from your Account Settings:

Note: if an app will have other users, you can implement [authorization with OAuth1](https://api.smugmug.com/api/v2/doc/tutorial/authorization.html), but this is left as an exercise to the reader.

### Future improvements

Future improvements could include better default selections (based on which image has been tagged or titled, but we don't do a lot of that).

I would also like to learn to use the `Grid` layout instead of `Pack` in `tkinter`, so I can create a table of image attributes instead of long image labels.
