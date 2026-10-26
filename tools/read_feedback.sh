#!/usr/bin/env bash
# List recent giscus feedback (GitHub Discussions, Announcements category) for the Daily Brief.
# Usage: tools/read_feedback.sh [N discussions, default 30]
set -euo pipefail
N="${1:-30}"
gh api graphql -F n="$N" -f query='
query($n:Int!){ repository(owner:"matiasriccibrochiero", name:"daily-brief"){
  discussions(first:$n, categoryId:"DIC_kwDOVQx5Js4DJrHP", orderBy:{field:UPDATED_AT, direction:DESC}){
    nodes{ number title url createdAt updatedAt
      reactionGroups{ content reactors{ totalCount } }
      comments(first:50){ nodes{ createdAt author{login} body
        reactionGroups{ content reactors{ totalCount } }
        replies(first:20){ nodes{ createdAt author{login} body } } } } } } } }' \
| jq -r '
  def rx: [.[] | select(.reactors.totalCount>0) | "\(.content)=\(.reactors.totalCount)"] | if length==0 then "none" else join(", ") end;
  .data.repository.discussions.nodes as $d
  | if ($d|length)==0 then "No feedback discussions yet." else
    ($d[] | "== \(.title)  (#\(.number), updated \(.updatedAt))\n   \(.url)\n   reactions: \(.reactionGroups|rx)\n"
      + ( [ .comments.nodes[] | "   - [\(.createdAt)] \(.author.login // "ghost"): \(.body|gsub("\r?\n";" "))"
            + (if (.reactionGroups|rx)!="none" then "  {\(.reactionGroups|rx)}" else "" end)
            + ( [ .replies.nodes[] | "\n       ↳ [\(.createdAt)] \(.author.login // "ghost"): \(.body|gsub("\r?\n";" "))" ] | join("") ) ]
          | if length==0 then "   comments: none" else join("\n") end ) + "\n")
    end'
