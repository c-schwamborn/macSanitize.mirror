#### Summary

This script was written to remove certain characters from file/directory names and remove spaces where they do not belong in SMB shares. Most commonly this happens if there are Apple computers around 😉 

#### Overview

If you are migrating Apple servers towards Linux/Samba file servers, or switch your old infrastructure running AFP via Netatalk to modern Samba file sharing, you will most likely run into the issue of inaccessible files, empty folders and other strange things on your network drives.

The main causes for those issues are two things:

First, is the data comes from a Mac server, you have to overcome the name encoding difference between Apple and the rest of the world.

Second, as Mac allows any character in its folder and file names, you need to sanitize your file structure, since Samba follows the SMB naming specifications, whereas AFP and Apples SMB implementation allows any sort of ugly stuff besides certain characters, like spaces at the beginning and ending of a folder or filename.  
On a Windows machine those spaces are stripped upon creation and never exist on disk, but Macs do create them. Actually quite often, even if the users create them on purpose. They just appear, most common by accidentally copying something (with a space at the end) for the filename.

That second problem which is the focus of this project: Replacing certain characters from file and folder names by something safe like an underscore(\_) and stripping superfluous leading or trailing spaces. Optionally the script also removes spaces before and after the file extension dot, although a file with spaces at the base file name isn't a real issue, it can be annoying and that space is useless anyways.

#### Data transfer from a Mac

This is just a short summery of the process as other sources on the net explain this in depth.

There are different ways to perform this copy process by mounting the new Samba shares on the old Apple server and do the copying there with tools like rsync or ditto, mounting the old Mac shares on Linux and trying to copy the data from that end, or using rsync over ssh (I personally  recommend this) from either side - Mac or the Linux side.

Using rsync, you must not use the stock rsync version of MacOS, as it is Years old and doesn't support the features you'll need - install something from Homebrew or suchlike. On the Linux side you'll most likely be fine on any recent distribution.

As for the parameters:

```shell
rsync --recursive --links --times --hard-links \
--8-bit-output --iconv=utf-8,utf-8-mac \
--ignore-errors --numeric-ids \
--rsync-path=/usr/local/bin/rsync \
--exclude ".Spotlight-V100" \
--exclude ".fseventsd" \
--log-file=tranfer.log \
adminuser@<servername_or_ip>:/some/path/shared/. \
/new/path/shared/. 2>>tranfer_error.log
```

Optionally, but in my opinion useless as you have to set permissions and ownership after the transfer anyways, some use the parameter *\--executability* .

Don't use *\--xattrs* as some suggest. In my experience this is just cause for lots of errors with no benefit. Copying the extended attributes often fail as the Apple attributes won't fit into the attribute space your Linux system, depending on your used filesystem. Furthermore most of the information is structured Mac specific and Samba doesn't recognize them anyway as it does its own usage of extended attributes.

Depending on the system you are performing the copy from, use *iconv=utf-8,utf-8-mac* if you initiate the copy process from the Linux system and *iconv=utf-8-mac,utf-8* if you are copying from the Mac side. The coding order has nothing to do with the copy direction, but it defines the local and remote filesystem encoding. So Linux is allways *utf-8* and Mac is *utf-8-mac* .

The option *\--rsync-path* is needed to specify the correct rsync on the mac side, otherwise you end up using Apples stock version of rsync which will fail.

You just need to adjust permissions and ownership afterwards i.e.:

```
chown --recursive <somename> /new/path/shared
chgrp --recursive <somegroup> /new/path/shared
find /new/path/shared -type d -print0 | xargs -0 chmod 2770
find /new/path/shared -type f -print0 | xargs -0 chmod 660
```

#### Usage and technical details

The script can do the following things for you:

1. Remove ugly characters from names that do not belong onto a SMB share.
2. Remove trailing spaces from names.
3. Remove leading spaces from names. Not necessary, but not very useful either and often cause for confusion, since the automatic listing order might be off without an obvious reason.
4. Remove spaces around the extension dot(.) after the base file (quiet often case) name and leading the actual extension (unlikely but it occurs).

There is a built-in feature preventing name conflicts that might result from renaming or stripping away spaces. If an already existing name is discovered, a numeric index is appended to the name, in case of files before the extension.

Example command to do the above on directories and files:

```
macSanitize.py -f -d -l -t -e -u /path/to/sanitize/
```

To get more options and some help, call the script with *\--help* .

```
./macSanitize.py --help
```

I strongly advise to backup your data, test the process on snapshots first, or at least do a dry run ( *\--dryrun* ) before starting the actually renaming process.

#### Issues

Only the renaming in the current work folder is presented in the dry run log. The logs will show up the original folder names further down, once the process descends into the next level, as the script has to work its way though the actual file structure.