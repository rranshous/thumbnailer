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

GEARMAN_HOSTS = []

from gearmanlib import helpers

def get_key(url,size='full'):
    import os
    key = '%s_%s' % (size,url)
    key = key.replace(os.sep,'_')
    return key

def gearman_download_resource(url):
    from gearmanlib import helpers
    return helpers.call_gearman(helpers.get_key(download_resource),
                                url,hosts=GEARMAN_HOSTS)

@helpers.farmable
def download_resource(url):
    from urllib2 import urlopen
    try:
        data = urlopen(url).read()
    except Exception, ex:
        return None
    return data

def gearman_thumbnail_image(size,data=None,in_path=None,out_path=None):
    from gearmanlib import helpers
    return helpers.call_gearman(helpers.get_key(thumbnail_image),
                                size,data,in_path,out_path,
                                hosts=GEARMAN_HOSTS)

@helpers.farmable
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


def get_thumbnail(storage_root,full_url,size):
    from diskdb import SimpleBlip as Blip
    import urlparse
    size = str(size) # we need a string
    parsed = urlparse.urlparse(full_url) # break up our url to strip args
    url = '%s://%s%s' % (parsed.scheme,parsed.netloc,parsed.path) # recreate
    key = get_key(url,size) # get the key for this file's storage
    print 'key: %s' % key

    # check and see if we have the thumbnail already
    thumbnail = Blip(storage_root,key)
    thumbnail_data = thumbnail.get_value()

    # if we don't have the thumbnail check and see if
    # we have the original
    if not thumbnail_data:
        print 'no thumbnail data'
        original = Blip(storage_root,get_key(url))
        original_data = original.get_value()

    # if we don't have the original send off a task to
    # download it
    if not thumbnail_data and not original_data:
        print 'no original data'
        original_data = download_resource(url,farm=True)
        original.set_value(original_data)
        original.flush()

    if not thumbnail_data:
        print 'creating thumbnail'
        # now that we've downloaded it we need to get it resized
        thumbnail_data = thumbnail_image(size,original_data,farm=True)
        thumbnail.set_value(thumbnail_data)
        thumbnail.flush()

    return thumbnail_data

