#!/usr/bin/env bash
# Publish one exercise folder onto its own long-lived branch **flattened**:
# the contents of <folder>/ become the branch root, so that README.md, code/,
# docs/, diagrams/, output/ and tests/ sit at the top level of the branch and
# GitHub renders the exercise README directly when the branch is opened.
#
# The branch is NOT checked out: a temporary index is built from the branch tip,
# the old <folder>/ prefix is dropped, the working-tree folder is staged at the
# root on top of it, and the resulting commit is pushed.
#
# Usage:  tools/push_flat.sh <branch> <folder> "<commit message>"
set -euo pipefail

BR="${1:?branch name required}"
DIR="${2:?folder required}"
MSG="${3:?commit message required}"

cd "$(git rev-parse --show-toplevel)"
[ -d "$DIR" ] || { echo "folder $DIR does not exist" >&2; exit 1; }

git fetch -q origin "refs/heads/${BR}:refs/remotes/origin/${BR}"
git rev-parse --verify -q "origin/${BR}" >/dev/null \
  || { echo "branch ${BR} does not exist on origin" >&2; exit 1; }

TMP_INDEX="$(mktemp -u /tmp/flat-index.XXXXXX)"
export GIT_INDEX_FILE="${TMP_INDEX}"

git read-tree "origin/${BR}"

# 1. drop the old nested layout (exercise-N/...) from the branch index
if git ls-files --error-unmatch -- "${DIR}" >/dev/null 2>&1; then
  git rm -r -q --cached -f -- "${DIR}"
fi

# 2. stage the working-tree folder as the branch ROOT
git --work-tree="${DIR}" add -A -- .

# 3. keep the repo-level files that belong to every branch (they live outside
#    the exercise folder, so the step above would otherwise delete them)
for p in PROJECT_PROGRESS.md Multilevel_Queue_Scheduling.py \
         EXERCISE_BRANCH_INDEX.md assets; do
  if [ -e "$p" ]; then
    git add -A -- "$p"
  fi
done

TREE="$(git write-tree)"
unset GIT_INDEX_FILE
rm -f "${TMP_INDEX}"

PARENT="$(git rev-parse "origin/${BR}")"
COMMIT="$(git commit-tree "${TREE}" -p "${PARENT}" -m "${MSG}")"

LOCAL_REF="refs/heads/push-flat-${BR}"
git update-ref "${LOCAL_REF}" "${COMMIT}"
git push origin "${LOCAL_REF}:refs/heads/${BR}"
git update-ref -d "${LOCAL_REF}"

echo "pushed ${DIR}/* -> ${BR} (root) as ${COMMIT:0:8}"
