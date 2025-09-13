#!/bin/bash

CONTAINER_NAME="kuzushi-postgres"
DB_USER="postgres"
DB_PASSWORD="zindabaad2491" # Using the password you updated
DB_NAME="prmdb"

echo "Attempting to configure database '$DB_NAME' for user '$DB_USER' in Docker container '$CONTAINER_NAME'..."

# Step 1: Set/Update the password for the 'postgres' user
echo "Setting password for user '${DB_USER}'..."
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
if [ $? -ne 0 ]; then
    echo "Error setting password for user '${DB_USER}'. Exiting."
    exit 1
else
    echo "Password for user '${DB_USER}' set successfully."
fi

# Step 2: Check if database exists and create it if it doesn't
echo "Checking if database '${DB_NAME}' exists..."
DB_EXISTS_CHECK_COMMAND="SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'"
# The -t option removes headers, -A removes alignment, -c executes command
DB_EXISTS_OUTPUT=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -tAc "${DB_EXISTS_CHECK_COMMAND}")

if [ "$DB_EXISTS_OUTPUT" = "1" ]; then
    echo "Database '${DB_NAME}' already exists."
else
    echo "Database '${DB_NAME}' does not exist. Creating..."
    docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"
    if [ $? -eq 0 ]; then
        echo "Database '${DB_NAME}' created successfully."
    else
        echo "Failed to create database '${DB_NAME}'. Please check PostgreSQL logs in the container. Exiting."
        exit 1
    fi
fi

# Step 3: Grant privileges (Postgres user is superuser, but explicit grant is fine)
echo "Granting privileges on database '${DB_NAME}' to user '${DB_USER}'..."
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
if [ $? -ne 0 ]; then
    echo "Error granting privileges on database '${DB_NAME}' to user '${DB_USER}'. This might be non-critical if user is superuser."
else
    echo "Privileges granted successfully."
fi

echo ""
echo "Database '$DB_NAME' configuration process completed."
echo "---"
echo "SQL Connection String for your .env file:"
echo "DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}"
echo "---"
