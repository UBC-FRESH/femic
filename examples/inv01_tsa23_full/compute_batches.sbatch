#!/bin/bash
#SBATCH --account=st-gep-1
#SBATCH --partition=skylake
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=150G
#SBATCH --exclusive
#SBATCH --array=0-92%8
#SBATCH --job-name=inv01_compute
#SBATCH --output=%x_%A_%a.out
#
# Edit account, array range, and paths for the target allocation.
module load gcc/7.5.0 python/3.12.7
INV01_ROOT="${INV01_ROOT:?set INV01_ROOT}"
PYTHON="${PYTHON:?set PYTHON to the femic venv interpreter}"
export PYTHONPATH="${FEMIC_SRC:?set FEMIC_SRC to the femic src directory}"
RUNBOOK_DIR="${RUNBOOK_DIR:?set RUNBOOK_DIR to examples/inv01_tsa23_full}"
BATCH=$(printf "%04d" "$SLURM_ARRAY_TASK_ID")
MANIFEST="$INV01_ROOT/manifests/batches/batch_${BATCH}.csv"
OUT="$INV01_ROOT/parts/batch_${BATCH}.parquet"
if [ -s "$OUT" ]; then echo "already done $OUT"; exit 0; fi
if [ ! -s "$MANIFEST" ]; then echo "missing $MANIFEST"; exit 1; fi
"$PYTHON" "$RUNBOOK_DIR/process_batch.py" \
  "$MANIFEST" "$OUT" \
  --raw-root "$INV01_ROOT/raw" \
  --workers 24 \
  --origin-x 549275 \
  --origin-y 5784675 \
  --grid-size-m 25 \
  --min-returns 10 \
  --min-cover-pct 10
