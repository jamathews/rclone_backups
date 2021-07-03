# Restore Local Copy of Encrypted Backups

- Download your encrypted backups from B2 (or use their "ship me a hard drive" service if it's big)
- `rclone config`: make a "remote" of type local, call it "local"
- `rclone config`: make a second remote of type crypt, use "local:/path/to/encrypted/backups" as the remote to decrypt
- `rclone copy` or the restore script from this localcrypt remote as though it was a cloud storage remote

TODO: 
`rclone lsjson -R b2crypt:`
- parse json for IsDir:true, save paths in tracker.json
- reuse backup tracker, `rclone copy` will copy from remote to local