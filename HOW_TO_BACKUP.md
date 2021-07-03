# How To Prep For Backups

- install `rclone`
- `rclone config`
    - "New remote"
    - name: "b2"
    - key ID and Application Key as stored in password manager
- create a bucket in B2 web interface

## Optionally Make a Crypt Remote if you want files to be encrypted
 
- `rclone config`
  - "New remote"
  - name: "b2crypt"
  - Storage type: crypt
  - remote to encrypt/decrypt: "b2:/my-bucket"
  - filename_encryption: off
  - directory_name_encryption: false
  - password and salt: as stored in your password manager
  
 
TODO: rclone config, Set configuration password

# Run a backup

`./backup.py --sources "/path/to/important/files" "/path/to/more/important/files" --remote-name b2crypt --bucket-name my-bucket`


