#!/usr/bin/env bash
# Publish generated Euclid products on top of any concurrent archive commit.
set -euo pipefail

branch=research/euclid-dr1-foundation-day01-20261114
ref="refs/heads/$branch"
for attempt in 1 2 3 4; do
    if git push origin "HEAD:$ref"; then
        exit 0
    fi

    # An authentication or server error should remain visible. Retry only if
    # the remote advanced and the archive commit can be applied on top of it.
    git fetch --no-tags origin "$ref"
    if git merge-base --is-ancestor FETCH_HEAD HEAD; then
        exit 1
    fi
    git rebase FETCH_HEAD
    sleep "$attempt"
done

git push origin "HEAD:$ref"
