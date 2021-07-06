COMMIT=$(git rev-parse HEAD)
BRANCH=$(git status |head -1| cut -d' ' -f 3)
DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VERSION=$(git tag | tail -1)

[ ${#VERSION} == 0 ] && VERSION="no version"
echo "{
\"commit\":  \"$COMMIT\",
\"date\":    \"$DATE\",
\"branch\":  \"$BRANCH\",
\"version\": \"$VERSION\"
}"