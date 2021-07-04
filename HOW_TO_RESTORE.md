# Restore From Remote

1. Follow the "How To Prep For Backups" steps in [HOW_TO_BACKUP.md](HOW_TO_BACKUP.md)
1. Run `./backup.py --restore --remote-name <encrypted remote name> --sources "remote/path/to/backups" --destination "/local/path/for/restored/files"`

Run `./backup.py --help` for more options.

# Restore Local Copy of Encrypted Backups
1. Download your encrypted backups from B2 (or use their "ship me a hard drive" service if it's too big)
1. `rclone config`: make a "remote" of type local, call it "local"
1. `rclone config`: make a second remote of type crypt, use "local:/path/to/encrypted/backups" as the remote to decrypt
1. `rclone copy` or `./backup.py --restore --remote-name localcrypt ...`
