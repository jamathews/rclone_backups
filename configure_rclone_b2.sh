#!/usr/bin/env bash

if [[ ! `command -v rclone` ]]; then
	curl https://rclone.org/install.sh | sudo bash
fi

if [[ -z ${ACCOUNTID} ]]; then
    echo "\$ACCOUNTID is not defined. Please set this environment variable. Check your password manager for the correct value."
    exit 1
fi

if [[ -z ${KEYID} ]]; then
    echo "\KEYID is not defined. Please set this environment variable. Check your password manager for the correct value."
    exit 1
fi

if [[ -z ${CRYPT_REMOTE} ]]; then
    echo "\CRYPT_REMOTE is not defined. Please set this environment variable. Check your password manager for the correct value."
    exit 1
fi

if [[ -z ${PASSWORD} ]]; then
    echo "\PASSWORD is not defined. Please set this environment variable. Check your password manager for the correct value."
    exit 1
fi

if [[ -z ${SALT} ]]; then
    echo "\SALT is not defined. Please set this environment variable. Check your password manager for the correct value."
    exit 1
fi

rclone config create b2 b2 account "${ACCOUNTID}" key "${KEYID}"
rclone config create b2crypt crypt remote "${CRYPT_REMOTE}" filename_encryption "off" directory_name_encryption "false" password "${PASSWORD}" password2 "${SALT}"
