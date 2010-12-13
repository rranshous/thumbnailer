#!/usr/bin/python

## the goal is to:
# figure out what the query would be for if it were not 
#   against a sub domain
# download the image @ the url sans the sub domain
# resize the image to specified size and return
# caching along the way

## want to try and use gearman for resource aquisition
## as well as resizing

## pieces:
# resource downloader
# image re-sizer

## we are going to use the diskdb lib
## for data caching

## data mapping
# we are going to use the diskdb library to store image
# data, the key is going to be the non-full url

def get_key(url,size='full'):
    return '%s_%s' % (size,url)

def get_thumbnail(storage_root,full_url,size):
    from diskdb import SimpleBlip as Blip
    import urlparse
    size = str(size) # we need a string
    parsed = urlparse.urlparse(full_url) # break up our url to strip args
    url = '%s://%s%s' % (parsed.scheme,parsed.netloc,parsed.path) # recreate
    key = get_key(url,size) # get the key for this file's storage

    # check and see if we have the thumbnail already
    thumbnail = Blip(storage_root,key)
    thumbnail_data = thumbnail.get_value()

    # if we don't have the thumbnail check and see if
    # we have the original
    if not thumbnail_data:
        original = Blip(storage_root,get_key(url))
        original_data = original.get_value()

    # if we don't have the original send off a task to
    # download it
    if not thumbnail_data and not original_data:
        original_data = download_resource(url)
        original.set_value(original_data)
        original.flush()

    if not thumbnail_data:
        # now that we've downloaded it we need to get it resized
        thumbnail_data = thumbnail_image(size,original_data)
        thumbnail.set_value(thumbnail_data)
        thumbnail.flush()

    return thumbnail_data

def download_resource(url):
    from urllib2 import urlopen
    try:
        data = urlopen(url).read()
    except Exception, ex:
        return None
    return data

def thumbnail_image(size,data=None,in_path=None,out_path=None):
    import subprocess
    if data:
        print 'thumbnail_image data: %s' % len(data)
    if not in_path:
        in_path = '-'
    if not out_path:
        out_path = '-'
    cmd = ['convert','-thumbnail',size,in_path,out_path]
    print 'running: %s' % ' '.join(cmd)
    proc = subprocess.Popen(cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    (out_data,error) = proc.communicate(data)
    if error:
        print 'error from cmd: %s' % error
    if out_path == '-':
        return out_data
    return out_path
