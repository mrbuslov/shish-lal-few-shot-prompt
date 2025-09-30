#!/bin/bash
set -e

# Ждем пока MongoDB полностью запустится
sleep 5

echo "Creating application user..."

mongosh <<EOF
use ${MONGODB_DB_NAME}

db.createUser({
  user: "${MONGO_APP_USER}",
  pwd: "${MONGO_APP_PASSWORD}",
  roles: [
    {
      role: "readWrite",
      db: "${MONGODB_DB_NAME}"
    }
  ]
});

print('✅ User created successfully');
EOF
