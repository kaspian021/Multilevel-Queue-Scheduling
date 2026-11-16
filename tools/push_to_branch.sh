#!/usr/bin/env bash
# Publish one exercise folder onto its own long-lived branch.
#
# The branch is NOT checked out: a temporary index is built from the branch tip,
# the working-tree folder is staged on top of it, and the resulting commit is
# pushed.  This keeps the session branch untouched while each exercise branch
# only ever receives its own folder.
#
# Usage:  tools/push_to_branch.sh <branch> <folder> "<commit message>"
set -euo pipefail

BR="${1:?branch name required}"
DIR="${2:?folder required}"
MSG="${3:?commit message required}"

cd "$(git rev-parse --show-toplevel)"

git fetch -q origin "refs/heads/${BR}:refs/remotes/origin/${BR}"
if ! git rev-parse --verify -q "origin/${BR}" >/dev/null; then
  echo "branch ${BR} does not exist on origin" >&2
  exit 1
fi

TMP_INDEX="$(mktemp -u /tmp/branch-index.XXXXXX)"
export GIT_INDEX_FILE="${TMP_INDEX}"
git read-tree "origin/${BR}"
# shellcheck disable=SC2086
git add -A -- "${DIR}"
TREE="$(git write-tree)"
unset GIT_INDEX_FILE
rm -f "${TMP_INDEX}"

PARENT="$(git rev-parse "origin/${BR}")"
COMMIT="$(git commit-tree "${TREE}" -p "${PARENT}" -m "${MSG}")"

LOCAL_REF="refs/heads/push-tmp-${BR}"
git update-ref "${LOCAL_REF}" "${COMMIT}"
git push origin "${LOCAL_REF}:refs/heads/${BR}"
git update-ref -d "${LOCAL_REF}"

echo "pushed ${DIR} -> ${BR} as ${COMMIT:0:8}"
