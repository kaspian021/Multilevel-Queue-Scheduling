#!/usr/bin/env bash
# Publish one exercise folder of the LST project onto its own long-lived branch
# of the target repository, **flattened**: the contents of <folder>/ become the
# branch root, so that README.md, code/, docs/, diagrams/, output/ and tests/
# sit at the top level of the branch and GitHub renders the exercise README
# directly when the branch is opened.
#
# The branch is NOT checked out: a temporary index is built from the branch tip
# (or from nothing, when the branch does not exist yet), the old <folder>/
# prefix is dropped, the working-tree folder is staged at the root on top of
# it, and the resulting commit is pushed.
#
# Usage:
#   tools/push_lst.sh <branch> <folder> "<commit message>"
#   tools/push_lst.sh main . "message"          # push the whole tree as-is
#
# The remote defaults to REMOTE below and can be overridden with $LST_REMOTE.
set -euo pipefail

BR="${1:?branch name required}"
DIR="${2:?folder required}"
MSG="${3:?commit message required}"
REMOTE="${LST_REMOTE:-https://github.com/rera13197-ux/LST.git}"

cd "$(git rev-parse --show-toplevel)/lst"
[ -d "$DIR" ] || { echo "folder $DIR does not exist" >&2; exit 1; }

# Does the branch already exist on the remote?
EXISTING="$(git ls-remote --heads "$REMOTE" "refs/heads/${BR}" | head -n1 | cut -f1 || true)"

TMP_INDEX="$(mktemp -u /tmp/lst-index.XXXXXX)"
export GIT_INDEX_FILE="${TMP_INDEX}"

if [ -n "$EXISTING" ]; then
  git fetch -q "$REMOTE" "refs/heads/${BR}"
  git read-tree FETCH_HEAD
  # 1. drop the old nested layout (exercise-N/...) from the branch index
  if [ "$DIR" != "." ] && git ls-files --error-unmatch -- "$DIR" >/dev/null 2>&1; then
    git rm -r -q --cached -f -- "$DIR"
  fi
else
  echo "branch ${BR} does not exist on ${REMOTE} -- creating it"
fi

# 2. stage the folder at the branch ROOT (or the whole tree when DIR is ".")
if [ "$DIR" = "." ]; then
  git --work-tree="." add -A -- .
else
  git --work-tree="${DIR}" add -A -- .
fi

# 3. keep the repo-level files that belong on every branch
for p in PROJECT_PROGRESS.md EXERCISE_BRANCH_INDEX.md; do
  if [ -e "$p" ]; then
    git add -A -- "$p"
  fi
done

TREE="$(git write-tree)"
unset GIT_INDEX_FILE
rm -f "${TMP_INDEX}"

if [ -n "$EXISTING" ]; then
  COMMIT="$(git commit-tree "${TREE}" -p "${EXISTING}" -m "${MSG}")"
else
  COMMIT="$(git commit-tree "${TREE}" -m "${MSG}")"
fi

LOCAL_REF="refs/heads/push-lst-${BR}"
git update-ref "${LOCAL_REF}" "${COMMIT}"
git push "$REMOTE" "${LOCAL_REF}:refs/heads/${BR}"
git update-ref -d "${LOCAL_REF}"

echo "pushed ${DIR} -> ${BR} as ${COMMIT:0:8}"
