#!/usr/bin/env bash
source .env
for depth in $(seq 0 5)
do
  rclone purge b2://"rclone-backups-23bridgeport/encrypted/calliope.local"
  DB="./test/test-${depth}.db.sqlite3"
  LOG="./test/logs-${depth}"
  time \
   ./backup.py \
    -v \
    --backup \
    --tracker ${DB} \
    --logdir ${LOG} \
    --remote-name b2crypt \
    --sources ~/Documents \
    --depth ${depth} \
    | tee "./test/time-${depth}.log"
done
