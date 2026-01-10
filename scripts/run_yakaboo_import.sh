#!/bin/bash
# Quick helper to run Yakaboo import with proper environment

# Activate venv
source /home/ubuntu/onix_project/.venv/bin/activate

# Set database URL
export DATABASE_URL=postgresql://onix_user:onix_secure_pass_2024@localhost:5432/onix_db

# Run import with passed arguments
python /home/ubuntu/onix_project/scripts/import_yakaboo_prisma.py "$@"
