#!/usr/bin/env bash
##############################################################################
# Career Navigator — PostgreSQL backup and restore helper (Phase 7)
#
# Usage:
#   # Create a timestamped backup:
#   ./scripts/db_backup_restore.sh backup
#
#   # Restore from a specific file:
#   ./scripts/db_backup_restore.sh restore backups/career_navigator_20250301_030000.sql.gz
#
#   # List available backups:
#   ./scripts/db_backup_restore.sh list
#
# Environment variables (override defaults):
#   DB_HOST      — default: localhost
#   DB_PORT      — default: 5432
#   DB_NAME      — default: career_navigator
#   DB_USER      — default: postgres
#   PGPASSWORD   — set your password here (or use .pgpass)
#   BACKUP_DIR   — default: ./backups
#   S3_BUCKET    — if set, syncs backups to s3://<bucket>/db-backups/
#
# Retention: keeps last 7 local backups; S3 lifecycle handles cloud retention.
##############################################################################
set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-career_navigator}"
DB_USER="${DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
S3_BUCKET="${S3_BUCKET:-}"
RETENTION_COUNT=7

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

# ── Colours ───────────────────────────────────────────────────────────────
GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"; RESET="\033[0m"
info()  { echo -e "${GREEN}[INFO]${RESET}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ── Command dispatch ─────────────────────────────────────────────────────
CMD="${1:-help}"

case "$CMD" in

  # ── BACKUP ──────────────────────────────────────────────────────────────
  backup)
    info "Starting backup of ${DB_NAME} → ${BACKUP_FILE}"
    mkdir -p "${BACKUP_DIR}"

    # Verify pg_dump is available
    command -v pg_dump >/dev/null 2>&1 || error "pg_dump not found. Install postgresql-client."

    # Dump — plain SQL format, compressed
    pg_dump \
      -h "${DB_HOST}" \
      -p "${DB_PORT}" \
      -U "${DB_USER}" \
      -d "${DB_NAME}" \
      --no-password \
      --verbose \
      --format=plain \
      --no-acl \
      --no-owner \
    | gzip > "${BACKUP_FILE}"

    SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
    info "Backup complete: ${BACKUP_FILE} (${SIZE})"

    # Upload to S3 if configured
    if [[ -n "${S3_BUCKET}" ]]; then
      info "Uploading to s3://${S3_BUCKET}/db-backups/..."
      aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/db-backups/" \
        --storage-class STANDARD_IA
      info "Upload complete."
    fi

    # Prune old local backups (keep last N)
    info "Pruning local backups — keeping last ${RETENTION_COUNT}..."
    ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null \
      | tail -n +"$((RETENTION_COUNT + 1))" \
      | xargs -r rm -v

    info "Done."
    ;;

  # ── RESTORE ─────────────────────────────────────────────────────────────
  restore)
    RESTORE_FILE="${2:-}"
    [[ -z "${RESTORE_FILE}" ]] && error "Usage: $0 restore <backup-file.sql.gz>"
    [[ -f "${RESTORE_FILE}" ]] || error "File not found: ${RESTORE_FILE}"

    warn "This will DROP and recreate the database '${DB_NAME}' on ${DB_HOST}:${DB_PORT}."
    read -r -p "Are you sure? Type 'yes' to confirm: " CONFIRM
    [[ "${CONFIRM}" == "yes" ]] || { info "Aborted."; exit 0; }

    info "Dropping and recreating database..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
      -c "DROP DATABASE IF EXISTS ${DB_NAME};" \
      -c "CREATE DATABASE ${DB_NAME};"

    info "Restoring from ${RESTORE_FILE}..."
    gunzip -c "${RESTORE_FILE}" \
      | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"

    info "Restore complete. Running Alembic to ensure schema is current..."
    alembic upgrade head || warn "Alembic upgrade failed — run manually."

    info "Done."
    ;;

  # ── LIST ────────────────────────────────────────────────────────────────
  list)
    info "Local backups in ${BACKUP_DIR}:"
    if ls "${BACKUP_DIR}"/*.sql.gz 2>/dev/null; then
      echo ""
      info "Sizes:"
      du -sh "${BACKUP_DIR}"/*.sql.gz
    else
      warn "No local backups found in ${BACKUP_DIR}"
    fi

    if [[ -n "${S3_BUCKET}" ]]; then
      echo ""
      info "S3 backups in s3://${S3_BUCKET}/db-backups/:"
      aws s3 ls "s3://${S3_BUCKET}/db-backups/" --human-readable --summarize
    fi
    ;;

  # ── VERIFY ──────────────────────────────────────────────────────────────
  verify)
    VERIFY_FILE="${2:-$(ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -1)}"
    [[ -z "${VERIFY_FILE}" ]] && error "No backup file found to verify."
    info "Verifying backup integrity: ${VERIFY_FILE}"
    gunzip -t "${VERIFY_FILE}" && info "OK — backup is valid gzip." || error "Backup is corrupted."
    ;;

  # ── HELP ─────────────────────────────────────────────────────────────────
  *)
    echo "Usage: $0 {backup|restore <file>|list|verify [file]}"
    echo ""
    echo "  backup              — create timestamped backup"
    echo "  restore <file.gz>   — restore from a backup file"
    echo "  list                — list available backups"
    echo "  verify [file.gz]    — verify backup integrity (defaults to latest)"
    ;;

esac
