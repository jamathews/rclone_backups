#!/usr/bin/env bash

if [[ ! `command -v rclone` ]]; then
	curl https://rclone.org/install.sh | sudo bash
fi

rclone config create b2 b2 account ${ACCOUNTID} key ${KEYID}
rclone config create b2crypt crypt remote ${CRYPT_REMOTE} filename_encryption "off" directory_name_encryption "false" password ${PASSWORD} password2 ${SALT}

