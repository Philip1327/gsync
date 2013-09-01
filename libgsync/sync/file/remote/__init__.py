# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re
from libgsync.output import verbose, debug, itemize
from libgsync.sync.file import SyncFile, SyncFileInfo
from libgsync.options import GsyncOptions
from apiclient.http import MediaIoBaseUpload
from libgsync.drive import Drive

class SyncFileRemote(SyncFile):
    def __init__(self, path):
        super(SyncFileRemote, self).__init__(path)
        self._path = self.normpath(path)

    def normpath(self, path):
        return Drive().normpath(path)

    def strippath(self, path):
        return Drive().strippath(path)

    def getPath(self, path = None):
        if path is None or path == "":
            return self._path

        selfStripPath = self.strippath(self._path)
        stripPath = self.strippath(path)

        debug("Joining: '%s' with '%s'" % (selfStripPath, stripPath))
        ret = self.normpath(os.path.join(selfStripPath, stripPath))

        debug(" * got: '%s'" % ret)
        return ret

    def getUploader(self, path = None):
        info = self.getInfo(path)
        if info is None:
            raise Exception("Could not obtain file information: %s" % path)

        path = self.getPath(path)
        drive = Drive()

        debug("Opening remote file for reading: %s" % path)

        f = drive.open(path, "r")
        if f is None:
            raise Exception("Open failed: %s" % path)

        return MediaIoBaseUpload(f, info.mimeType, resumable=True)

    def getInfo(self, path = None):
        path = self.getPath(path)

        debug("Fetching remote file metadata: %s" % path)

        # The Drive() instance is self caching.
        drive = Drive()

        info = drive.stat(path)
        if info is None:
            debug("File not found: %s" % path)
            return None

        debug("Remote file metadata = %s" % str(info))
        info = SyncFileInfo(**info)
        debug("Remote mtime: %s" % info.modifiedDate)

        return info

    def _createDir(self, path, src = None):
        debug("Creating remote directory: %s" % path)

        if not GsyncOptions.dry_run:
            drive = Drive()
            drive.mkdir(path)

    def _createFile(self, path, src):
        debug("Creating remote file: %s" % path)

        if GsyncOptions.dry_run: return

        drive = Drive()
        info = drive.create(path, src.getInfo())

        if info is None:
            debug("Creation failed")

    def _updateFile(self, path, src):
        debug("Updating remote file: %s" % path)

        self.bytesWritten = 0

        if GsyncOptions.dry_run: return

        drive = Drive()
        info = drive.update(path, src.getInfo(), src.getUploader())

        if info is not None:
            self.bytesWritten = long(info.get('fileSize', '0'))
        else:
            debug("Update failed")

    def _updateStats(self, path, src, mode, uid, gid, mtime, atime):
        debug("Updating remote file stats: %s" % path)

        if GsyncOptions.dry_run: return

        info = self.getInfo(path)
        if not info: return

        st_info = list(tuple(info.statInfo))

        if mode is not None:
            st_info[0] = mode
        if uid is not None:
            st_info[4] = uid
        if gid is not None:
            st_info[5] = gid
        if atime is not None:
            st_info[7] = atime
        if mtime is not None:
            st_info[8] = mtime
        
        info._setStatInfo(st_info)
            
        Drive().update(path, { 'description': info.description })