# How To Prep For Backups

## Automated
run `./configure_rclone_b2.sh`

## Manual
1. [Install `rclone`](https://rclone.org/install/).
1. Run `rclone config` Create a new remote of the appropriate type for the cloud storage you want 
   to use. Provide the requested credentials.

## Optionally Make a Crypt Remote if you want files to be encrypted
1. Run `rclone config`. Create a new remote of type `crypt`. When prompted for the remote to 
   encrypt, give it the remote name from the previous step.
1. Set `filename_encryption` to `off`
1. Set `directory_name_encryption` to `false`
1. Provide a password and salt when prompted.

# Run a backup
1. Install `python3.9` or higher
2. Run `./backup.py --sources "/path/to/important/files" "/path/to/more/important/files" --remote-name [remote name|encrypted remote name] --destination <destination/bucket name on remote>`

Run `./backup.py --help` for more options.
